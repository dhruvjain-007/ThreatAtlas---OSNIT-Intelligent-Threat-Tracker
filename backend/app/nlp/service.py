import spacy
from typing import List
from app.nlp.schemas import NLPResult, Entity, Location
from app.nlp.preprocessing import clean_text
from app.nlp.geocoder import geocode, fallback_country_geocode

class NLPService:
    def __init__(self):
        self.nlp = None

    def _load_model(self):
        if self.nlp is None:
            print("Loading spaCy model en_core_web_sm (disable parser, lemmatizer)...")
            self.nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
            
            # Setup EntityRuler
            ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            patterns = [
                # Military / Security Equipment
                {"label": "EQUIPMENT", "pattern": "T-72"},
                {"label": "EQUIPMENT", "pattern": "F-16"},
                {"label": "EQUIPMENT", "pattern": "drone"},
                {"label": "EQUIPMENT", "pattern": "drones"},
                {"label": "EQUIPMENT", "pattern": "UAV"},
                {"label": "EQUIPMENT", "pattern": "tank"},
                {"label": "EQUIPMENT", "pattern": "tanks"},
                {"label": "EQUIPMENT", "pattern": "missile"},
                {"label": "EQUIPMENT", "pattern": "missiles"},
                {"label": "EQUIPMENT", "pattern": "artillery"},
                {"label": "EQUIPMENT", "pattern": "navy"},
                {"label": "EQUIPMENT", "pattern": "warship"},
                {"label": "EQUIPMENT", "pattern": "troops"},
                # Conflict Event Types & Actions
                {"label": "EVENT_TYPE", "pattern": "airstrike"},
                {"label": "EVENT_TYPE", "pattern": "explosion"},
                {"label": "EVENT_TYPE", "pattern": "protest"},
                {"label": "EVENT_TYPE", "pattern": "offensive"},
                {"label": "EVENT_TYPE", "pattern": "shelling"},
                {"label": "EVENT_TYPE", "pattern": "strike"},
                {"label": "EVENT_TYPE", "pattern": "strikes"},
                {"label": "EVENT_TYPE", "pattern": "intercept"},
                {"label": "EVENT_TYPE", "pattern": "patrol"},
                {"label": "EVENT_TYPE", "pattern": "clashes"},
                {"label": "EVENT_TYPE", "pattern": "clash"},
                {"label": "EVENT_TYPE", "pattern": "border"},
                {"label": "EVENT_TYPE", "pattern": "casualty"},
                {"label": "EVENT_TYPE", "pattern": "casualties"},
                {"label": "EVENT_TYPE", "pattern": "ceasefire"},
                {"label": "EVENT_TYPE", "pattern": "bombing"},
                {"label": "EVENT_TYPE", "pattern": "riot"},
            ]
            ruler.add_patterns(patterns)
            print("spaCy model loaded with EntityRuler.")

    async def process_text(self, text: str) -> NLPResult:
        self._load_model()
        cleaned = clean_text(text)
        doc = self.nlp(cleaned)
        
        entities = []
        locations = []
        organizations = []
        equipment = []
        event_types = []
        
        # We will keep track of processed location texts to avoid duplicate geocoding
        processed_locs = set()
        
        for ent in doc.ents:
            entities.append(Entity(
                text=ent.text,
                label=ent.label_,
                start_char=ent.start_char,
                end_char=ent.end_char
            ))
            
            if ent.label_ in ["GPE", "LOC"]:
                loc_text = ent.text
                if loc_text not in processed_locs:
                    processed_locs.add(loc_text)
                    geo_res = await geocode(loc_text)
                    if geo_res:
                        locations.append(Location(
                            name=loc_text,
                            lat=geo_res[0],
                            lng=geo_res[1],
                            confidence="high", # Simple heuristic for MVP
                            country_code=geo_res[2] if len(geo_res) > 2 else None
                        ))
                    else:
                        locations.append(Location(
                            name=loc_text,
                            lat=0.0,
                            lng=0.0,
                            confidence="unknown"
                        ))
            
            elif ent.label_ == "ORG":
                organizations.append(ent.text)
                
            elif ent.label_ == "EQUIPMENT":
                equipment.append(ent.text)
                
            elif ent.label_ == "EVENT_TYPE":
                event_types.append(ent.text)

        # Fall back to country-level entity mentions if city NER extraction failed to find coordinates
        has_valid_coords = any(loc.lat != 0.0 or loc.lng != 0.0 for loc in locations)
        if not has_valid_coords:
            country_fallback = fallback_country_geocode(doc.ents, cleaned)
            if country_fallback:
                c_name, c_lat, c_lng, c_cc = country_fallback
                # Filter out any placeholder (0.0, 0.0) location with the same name if present
                locations = [loc for loc in locations if loc.name.lower() != c_name.lower() or (loc.lat != 0.0 or loc.lng != 0.0)]
                locations.insert(0, Location(
                    name=c_name,
                    lat=c_lat,
                    lng=c_lng,
                    confidence="country_fallback",
                    country_code=c_cc
                ))
                
        # Deduplicate lists
        organizations = list(set(organizations))
        equipment = list(set(equipment))
        event_types = list(set(event_types))
                
        return NLPResult(
            original_text=text,
            cleaned_text=cleaned,
            entities=entities,
            locations=locations,
            organizations=organizations,
            equipment=equipment,
            event_types=event_types
        )

nlp_service = NLPService()

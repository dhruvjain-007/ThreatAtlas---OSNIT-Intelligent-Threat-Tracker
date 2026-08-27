import React, { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import type { Event } from '../types';

interface HeatmapCell {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
  intensity: number;
  count: number;
}

const aggregateThreatGrid = (events: Event[], cellSize = 2): Map<string, HeatmapCell> => {
  const grid = new Map<string, HeatmapCell>();

  events.forEach((evt) => {
    if (!evt.location || !Array.isArray(evt.location.coordinates) || evt.location.coordinates.length < 2) return;

    let lon = Number(evt.location.coordinates[0]);
    let lat = Number(evt.location.coordinates[1]);

    if (isNaN(lon) || isNaN(lat)) return;
    if (lat < -90 || lat > 90) return;

    // Normalize lon to [-180, 180]
    lon = ((lon + 180) % 360 + 360) % 360 - 180;

    const cellMinLon = Math.floor(lon / cellSize) * cellSize;
    let cellMinLat = Math.floor(lat / cellSize) * cellSize;

    // Fix: Prevent maxLat from exceeding 90, which crashes Cesium.Rectangle
    if (cellMinLat >= 90) {
      cellMinLat = 90 - cellSize;
    }

    const key = `${cellMinLon},${cellMinLat}`;

    const existing = grid.get(key);
    if (existing) {
      existing.intensity += evt.threat_score;
      existing.count += 1;
    } else {
      grid.set(key, {
        minLon: cellMinLon,
        minLat: cellMinLat,
        maxLon: cellMinLon + cellSize,
        maxLat: cellMinLat + cellSize,
        intensity: evt.threat_score,
        count: 1,
      });
    }
  });

  return grid;
};

interface GlobeViewerProps {
  events: Event[];
  selectedEvent: Event | null;
  onSelectEvent: (event: Event) => void;
  showHeatmap?: boolean;
}

export const GlobeViewerComponent: React.FC<GlobeViewerProps> = ({
  events,
  selectedEvent,
  onSelectEvent,
  showHeatmap = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);

  // Initialize Cesium Viewer ONCE
  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return;

    // Set Ion default token
    Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI0YTYyZTk0Yy0yY2UwLTQyOWEtOWU3Yi04YjA1YWM2MGQ3MjYiLCJpZCI6MTU3MzA2LCJpYXQiOjE2OTA0OTkxMzR9.mock';

    const viewer = new Cesium.Viewer(containerRef.current, {
      requestRenderMode: true,
      maximumRenderTimeChange: Infinity,
      baseLayer: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: true,
      infoBox: false,
      sceneModePicker: false,
      selectionIndicator: false,
      timeline: false,
      animation: false,
      navigationHelpButton: false,
      scene3DOnly: true,
      shadows: false,
      terrainShadows: Cesium.ShadowMode.DISABLED,
      skyAtmosphere: false,
    });

    // 1. Crisp High-DPI Resolution & Antialiasing
    viewer.resolutionScale = window.devicePixelRatio || 1.0;
    if (viewer.scene.postProcessStages?.fxaa) {
      viewer.scene.postProcessStages.fxaa.enabled = true;
    }

    // 2. High-Quality Globe Imagery
    const imageryProvider = new Cesium.OpenStreetMapImageryProvider({
      url: 'https://a.tile.openstreetmap.org/',
    });
    viewer.imageryLayers.add(new Cesium.ImageryLayer(imageryProvider));

    // Dark atmosphere and globe styling with maximumScreenSpaceError
    const scene = viewer.scene;
    scene.globe.enableLighting = false;
    scene.globe.baseColor = Cesium.Color.fromCssColorString('#090d16');
    scene.globe.maximumScreenSpaceError = 2;
    scene.backgroundColor = Cesium.Color.fromCssColorString('#030712');

    // Click handler for threat markers
    const handler = new Cesium.ScreenSpaceEventHandler(scene.canvas);
    handler.setInputAction((movement: any) => {
      const pickedObject = scene.pick(movement.position);
      if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.properties) {
        const eventId = pickedObject.id.properties.eventId?.getValue();
        if (eventId) {
          const targetEvent = events.find((e) => e.id === eventId);
          if (targetEvent) {
            onSelectEvent(targetEvent);

            // Execute camera flyTo on marker click
            if (targetEvent.location?.coordinates && targetEvent.location.coordinates.length >= 2) {
              const lon = Number(targetEvent.location.coordinates[0]);
              const lat = Number(targetEvent.location.coordinates[1]);
              if (!isNaN(lon) && !isNaN(lat) && (lon !== 0 || lat !== 0)) {
                viewer.camera.flyTo({
                  destination: Cesium.Cartesian3.fromDegrees(lon, lat, 150000),
                  duration: 1.8,
                });
              }
            }
          }
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    viewerRef.current = viewer;

    return () => {
      handler.destroy();
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, []);

  // Update Entities when events list changes
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    let needsRender = false;
    const currentEventIds = new Set<string>();

    events.forEach((evt) => {
      if (!evt.location || !Array.isArray(evt.location.coordinates) || evt.location.coordinates.length < 2) {
        return;
      }

      const lon = Number(evt.location.coordinates[0]);
      const lat = Number(evt.location.coordinates[1]);

      if (isNaN(lon) || isNaN(lat) || (lon === 0 && lat === 0)) {
        return;
      }

      currentEventIds.add(evt.id);

      let color = Cesium.Color.fromCssColorString('#10B981'); // Low: Emerald Green
      let pointSize = 16;
      let outlineWidth = 2;

      if (evt.threat_level === 'High') {
        color = Cesium.Color.fromCssColorString('#EF4444'); // High: Crimson Red
        pointSize = 24;
        outlineWidth = 3.5;
      } else if (evt.threat_level === 'Medium') {
        color = Cesium.Color.fromCssColorString('#F97316'); // Medium: Amber/Orange
        pointSize = 20;
        outlineWidth = 2.5;
      }

      const position = Cesium.Cartesian3.fromDegrees(lon, lat, 500);
      const labelText = `${evt.title} [${evt.threat_level.toUpperCase()}]`;

      const existingEntity = viewer.entities.getById(evt.id);

      if (existingEntity) {
        // Update existing entity properties
        if (existingEntity.position) {
          (existingEntity.position as any).setValue(position);
        }
        if (existingEntity.point) {
          existingEntity.point.color = new Cesium.ConstantProperty(color);
          existingEntity.point.pixelSize = new Cesium.ConstantProperty(pointSize);
          existingEntity.point.outlineWidth = new Cesium.ConstantProperty(outlineWidth);
        }
        if (existingEntity.label) {
          existingEntity.label.text = new Cesium.ConstantProperty(labelText);
          existingEntity.label.fillColor = new Cesium.ConstantProperty(color);
        }
        needsRender = true;
      } else {
        // Create new entity
        viewer.entities.add({
          id: evt.id,
          position: position,
          point: {
            pixelSize: pointSize,
            color: color,
            outlineColor: Cesium.Color.WHITE.withAlpha(0.9),
            outlineWidth: outlineWidth,
            heightReference: Cesium.HeightReference.NONE,
          },
          label: {
            text: labelText,
            font: 'bold 11px monospace',
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineWidth: 2,
            outlineColor: Cesium.Color.BLACK,
            fillColor: color,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -14),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 5000000),
          },
          properties: {
            eventId: evt.id,
          },
        });
        needsRender = true;
      }
    });

    // Remove entities that are no longer in the events list
    // Safe check using existing eventId property to avoid removing unrelated entities
    const entitiesToRemove: Cesium.Entity[] = [];
    viewer.entities.values.forEach((entity) => {
      const eventId = entity.properties?.eventId?.getValue();
      if (eventId && !currentEventIds.has(eventId)) {
        entitiesToRemove.push(entity);
      }
    });

    if (entitiesToRemove.length > 0) {
      entitiesToRemove.forEach((entity) => {
        viewer.entities.remove(entity);
      });
      needsRender = true;
    }

    if (needsRender) {
      viewer.scene.requestRender();
    }
  }, [events]);

  const heatmapEntitiesRef = useRef<Cesium.Entity[]>([]);

  // Render Heatmap Layer
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    // 1. Clear previous heatmap entities
    heatmapEntitiesRef.current.forEach(entity => {
      viewer.entities.remove(entity);
    });
    heatmapEntitiesRef.current = [];

    // 2. If disabled, stop here and render
    if (!showHeatmap) {
      viewer.scene.requestRender();
      return;
    }

    // 3. Aggregate events into grid
    const grid = aggregateThreatGrid(events, 2);

    // 4. Find max intensity for normalization
    let maxIntensity = 0;
    grid.forEach(cell => {
      if (cell.intensity > maxIntensity) {
        maxIntensity = cell.intensity;
      }
    });

    if (maxIntensity === 0) {
      viewer.scene.requestRender();
      return;
    }

    // 5. Render normalized cells
    grid.forEach(cell => {
      const normalized = cell.intensity / maxIntensity;

      let color: Cesium.Color;
      if (normalized < 0.33) {
        color = Cesium.Color.fromCssColorString('#EAB308').withAlpha(0.2 + (normalized * 0.5)); // Yellow
      } else if (normalized < 0.66) {
        color = Cesium.Color.fromCssColorString('#F97316').withAlpha(0.3 + (normalized * 0.5)); // Orange
      } else {
        color = Cesium.Color.fromCssColorString('#DC2626').withAlpha(0.4 + (normalized * 0.5)); // Red
      }

      const rect = viewer.entities.add({
        rectangle: {
          coordinates: Cesium.Rectangle.fromDegrees(cell.minLon, cell.minLat, cell.maxLon, cell.maxLat),
          material: new Cesium.ColorMaterialProperty(color),
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          outline: false,
        }
      });

      heatmapEntitiesRef.current.push(rect);
    });

    viewer.scene.requestRender();
  }, [events, showHeatmap]);

  // Fly to selected event when changed from sidebar list or external state
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !selectedEvent || !selectedEvent.location?.coordinates) return;

    if (!Array.isArray(selectedEvent.location.coordinates) || selectedEvent.location.coordinates.length < 2) return;

    const lon = Number(selectedEvent.location.coordinates[0]);
    const lat = Number(selectedEvent.location.coordinates[1]);

    if (isNaN(lon) || isNaN(lat) || (lon === 0 && lat === 0)) return;

    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lon, lat, 150000),
      duration: 1.8,
    });
  }, [selectedEvent]);

  return (
    <div className="relative w-full h-full bg-slate-950">
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
};

export const GlobeViewer = React.memo(GlobeViewerComponent);

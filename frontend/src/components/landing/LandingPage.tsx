import React, { useEffect } from 'react';
import { LandingNavbar } from './LandingNavbar';
import { HeroSection } from './HeroSection';
import { LivePreviewSection } from './LivePreviewSection';
import { CapabilitiesSection } from './CapabilitiesSection';
import { WorkflowSection } from './WorkflowSection';
import { DashboardCTASection } from './DashboardCTASection';
import { LandingFooter } from './LandingFooter';

interface LandingPageProps {
  onNavigateDashboard: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigateDashboard }) => {
  const handleScrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  useEffect(() => {
    if (window.location.hash) {
      const id = window.location.hash.replace('#', '');
      const element = document.getElementById(id);
      if (element) {
        const timer = setTimeout(() => {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 80);
        return () => clearTimeout(timer);
      }
    }
  }, []);

  return (
    <div className="w-full min-h-screen bg-[#080D14] text-[#F1F5F9] font-sans selection:bg-cyan-500/30 selection:text-cyan-200 overflow-x-hidden">
      {/* Navigation Bar */}
      <LandingNavbar
        onNavigateDashboard={onNavigateDashboard}
        onScrollToSection={handleScrollToSection}
      />

      {/* Hero Section */}
      <main id="main-content">
        <HeroSection
          onNavigateDashboard={onNavigateDashboard}
          onScrollToSection={handleScrollToSection}
        />

        {/* Live Threat Intelligence Preview */}
        <LivePreviewSection onNavigateDashboard={onNavigateDashboard} />

        {/* Core Capabilities */}
        <CapabilitiesSection />

        {/* Pipeline Workflow */}
        <WorkflowSection />

        {/* High-Impact Dashboard Call-to-Action */}
        <DashboardCTASection onNavigateDashboard={onNavigateDashboard} />
      </main>

      {/* Footer */}
      <LandingFooter
        onNavigateDashboard={onNavigateDashboard}
        onScrollToSection={handleScrollToSection}
      />
    </div>
  );
};

import Navbar from "@/components/landing/Navbar";
import HeroSection from "@/components/landing/HeroSection";
import ClusterSection from "@/components/landing/ClusterSection";
import FeaturesSection from "@/components/landing/FeaturesSection";
import WaitlistSection from "@/components/landing/WaitlistSection";
import Footer from "@/components/landing/Footer";

export default function HomePage() {
  return (
    <main className="flex flex-col min-h-screen">
      <Navbar />
      <HeroSection />
      <ClusterSection />
      <FeaturesSection />
      <WaitlistSection />
      <Footer />
    </main>
  );
}

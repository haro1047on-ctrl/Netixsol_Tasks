import React, { useState } from "react";
import { motion, AnimatePresence, useScroll, useTransform, useSpring } from "framer-motion";
import {
  MapPin,
  Home,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Building2,
  ArrowUpRight,
  Sparkles,
} from "lucide-react";

// Curated luxury residences for the floating feature card carousel (matching reference photo)
const FEATURED_PROPERTIES = [
  {
    id: "01",
    total: "04",
    property_id: "PROP-1424",
    title: "EMBASSY LUXURY RESIDENCE",
    locality: "SECTOR F-7",
    city: "Islamabad",
    price: "PKR 28.0 Cr",
    rawPrice: 280000000,
    beds: 6,
    baths: 6,
    area_marla: 80.0,
    area_sqft: 21780.08,
    area: "4 Kanal (80 Marla)",
    sqft: "21,780 sqft",
    image: "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=80",
  },
  {
    id: "02",
    total: "04",
    property_id: "PROP-1009",
    title: "ROYAL HERITAGE ESTATE",
    locality: "MODEL TOWN",
    city: "Lahore",
    price: "PKR 27.0 Cr",
    rawPrice: 270000000,
    beds: 7,
    baths: 8,
    area_marla: 80.0,
    area_sqft: 21780.08,
    area: "4 Kanal (80 Marla)",
    sqft: "21,780 sqft",
    image: "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80",
  },
  {
    id: "03",
    total: "04",
    property_id: "PROP-1246",
    title: "SIGNATURE MODERN RESIDENCE",
    locality: "DHA DEFENCE",
    city: "Lahore",
    price: "PKR 12.5 Cr",
    rawPrice: 125000000,
    beds: 5,
    baths: 6,
    area_marla: 40.0,
    area_sqft: 10890.04,
    area: "2 Kanal (40 Marla)",
    sqft: "10,890 sqft",
    image: "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&q=80",
  },
  {
    id: "04",
    total: "04",
    property_id: "PROP-1376",
    title: "MARGALLA EXECUTIVE RESIDENCE",
    locality: "SECTOR F-6",
    city: "Islamabad",
    price: "PKR 10.25 Cr",
    rawPrice: 102500000,
    beds: 5,
    baths: 5,
    area_marla: 17.8,
    area_sqft: 4846.07,
    area: "18 Marla (4,846 sqft)",
    sqft: "4,846 sqft",
    image: "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=800&q=80",
  },
];

export default function HeroSection({
  totalProperties = 750,
  onExplore,
  onOpenVoice,
  onOpenAdminDemo,
  onSelectFeaturedProperty,
}) {
  const [featureIdx, setFeatureIdx] = useState(0);
  const currentFeature = FEATURED_PROPERTIES[featureIdx];

  // Silky parallax scrolling physics powered by Motion.dev useSpring pipeline
  const { scrollY } = useScroll();
  const smoothScrollY = useSpring(scrollY, {
    stiffness: 90,
    damping: 26,
    restDelta: 0.001,
  });
  const heroBgY = useTransform(smoothScrollY, [0, 900], [0, 210]);
  const heroBgScale = useTransform(smoothScrollY, [0, 900], [1.02, 1.15]);
  const heroContentY = useTransform(smoothScrollY, [0, 700], [0, -50]);
  const heroContentOpacity = useTransform(smoothScrollY, [0, 600], [1, 0.45]);

  const handlePrev = (e) => {
    e.stopPropagation();
    setFeatureIdx((prev) => (prev === 0 ? FEATURED_PROPERTIES.length - 1 : prev - 1));
  };

  const handleNext = (e) => {
    e.stopPropagation();
    setFeatureIdx((prev) => (prev === FEATURED_PROPERTIES.length - 1 ? 0 : prev + 1));
  };

  return (
    <section className="relative min-h-[90vh] lg:min-h-[95vh] w-full flex flex-col justify-between pt-28 sm:pt-32 pb-14 sm:pb-20 px-4 sm:px-8 overflow-hidden">
      {/* Background Hero Image with Cinematic Lighting & Smooth Parallax */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <motion.div
          style={{ y: heroBgY, scale: heroBgScale }}
          className="w-full h-full relative [mask-image:linear-gradient(to_bottom,black_0%,black_60%,transparent_98%)]"
        >
          <img
            src="/hero-bg.jpg"
            alt="Luxury Architecture Villa"
            className="w-full h-full object-cover object-center scale-105 filter brightness-[0.95] contrast-[1.05]"
          />
          {/* Soft Vignette and Cinematic Lighting Layers */}
          <div className="absolute inset-0 bg-gradient-to-r from-[#060910]/85 via-[#080c16]/40 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-b from-[#060910]/60 via-transparent to-[#090d16]" />
          {/* Warm Villa Interior Light Leak Effect */}
          <div className="absolute top-1/4 left-1/3 w-[36rem] h-[28rem] bg-[radial-gradient(ellipse,_rgba(245,180,100,0.12)_0%,_transparent_70%)] blur-3xl" />
        </motion.div>
      </div>

      {/* Ultra-Tall Seamless Transition Gradient at Bottom (Zero Harsh Edge, 100% Fluid Blend) */}
      <div className="absolute inset-x-0 bottom-0 h-72 sm:h-96 bg-gradient-to-t from-[#090d16] via-[#090d16]/90 via-[#090d16]/45 to-transparent pointer-events-none z-[5]" />

      {/* Main Hero Content Grid with Framer Motion Parallax */}
      <motion.div
        style={{ y: heroContentY, opacity: heroContentOpacity }}
        className="relative z-10 max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center my-auto"
      >
        {/* Left Column: Headline & Action Buttons */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="lg:col-span-7 space-y-6 text-left"
        >
          {/* Subtitle with accent line: REAL ESTATE, REIMAGINED ── */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="flex items-center gap-3"
          >
            <span className="text-xs sm:text-sm font-semibold tracking-[0.25em] text-amber-200/90 uppercase">
              Real Estate, Reimagined
            </span>
            <div className="w-14 h-[1.5px] bg-gradient-to-r from-amber-400/80 to-transparent" />
          </motion.div>

          {/* Majestic Serif Headline with Motion.dev Masked Text Reveal */}
          <motion.h1
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: {
                transition: {
                  staggerChildren: 0.14,
                  delayChildren: 0.15,
                },
              },
            }}
            className="font-display-serif text-5xl sm:text-6xl md:text-7xl lg:text-[80px] font-normal text-white leading-[1.05] tracking-tight"
          >
            {["Find a place", "that feels", "like yours."].map((line, idx) => (
              <span key={idx} className="block overflow-hidden py-0.5">
                <motion.span
                  className="block"
                  variants={{
                    hidden: { y: "115%", opacity: 0 },
                    visible: {
                      y: 0,
                      opacity: 1,
                      transition: {
                        duration: 0.85,
                        ease: [0.16, 1, 0.3, 1],
                      },
                    },
                  }}
                >
                  {line}
                </motion.span>
              </span>
            ))}
          </motion.h1>

          {/* Subtitle Description */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.35 }}
            className="text-slate-300 text-sm sm:text-base leading-relaxed max-w-lg font-light"
          >
            Carefully selected homes, apartments and commercial spaces for the way you actually want to live.
          </motion.p>

          {/* Hero Action Buttons - Styled to luxury golden amber & liquid glass theme */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.45 }}
            className="flex flex-wrap items-center gap-4 pt-2"
          >
            {/* Primary Golden Liquid CTA "Explore properties →" */}
            <motion.button
              whileHover={{ scale: 1.03, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={onExplore}
              className="relative px-7 py-3.5 rounded-full bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-bold text-xs sm:text-sm flex items-center gap-2 group cursor-pointer shadow-[0_4px_22px_rgba(245,180,100,0.4)] hover:shadow-[0_6px_28px_rgba(245,180,100,0.6)] transition-all overflow-hidden"
            >
              {/* Dynamic Shimmer Light Reflection Sweep on Hover */}
              <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/50 to-transparent pointer-events-none" />

              <span>Explore properties</span>
              <ArrowRight className="w-4 h-4 text-slate-950 group-hover:translate-x-1.5 transition-transform" />
            </motion.button>

            {/* "Talk with AI Agent" Button */}
            <motion.button
              whileHover={{ scale: 1.03, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={onOpenVoice}
              className="group flex items-center gap-3 px-5 py-3 rounded-full bg-[#101726]/85 hover:bg-white/[0.12] border border-white/20 hover:border-amber-400/50 backdrop-blur-2xl text-white transition-all cursor-pointer shadow-[0_10px_25px_rgba(0,0,0,0.5)]"
            >
              <div className="w-8 h-8 rounded-full bg-white/10 border border-white/15 flex items-center justify-center text-amber-300 group-hover:scale-110 group-hover:bg-amber-400/25 transition-all">
                <Sparkles className="w-4 h-4 text-amber-300" />
              </div>
              <span className="text-xs sm:text-sm font-semibold text-white group-hover:text-amber-200 transition-colors">
                Talk with AI Agent
              </span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse" />
            </motion.button>
          </motion.div>
        </motion.div>

        {/* Right Column: Floating Liquid Glass Feature Card (Matching Photo 1:1) */}
        <motion.div
          initial={{ opacity: 0, x: 30, scale: 0.96 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{ duration: 0.9, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="lg:col-span-5 flex justify-end"
        >
          <div className="w-full max-w-[340px] sm:max-w-[360px] liquid-feature-card p-4 sm:p-5 relative animate-float text-left bg-[#101726]/75 backdrop-blur-2xl border border-white/20 shadow-2xl">
            {/* Top Bar: Carousel Counter 01 / 04 & Arrows */}
            <div className="flex items-center justify-between mb-3 text-xs text-white font-mono">
              <div>
                <span className="font-bold text-white">{currentFeature.id}</span>
                <span className="text-slate-400 mx-1">/</span>
                <span className="text-slate-400">{currentFeature.total}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={handlePrev}
                  className="w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-slate-300 hover:text-white transition-colors cursor-pointer border border-white/15"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={handleNext}
                  className="w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-slate-300 hover:text-white transition-colors cursor-pointer border border-white/15"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Inset Residence Image with AnimatePresence */}
            <div className="relative h-44 sm:h-48 w-full rounded-2xl overflow-hidden mb-4 bg-slate-900 border border-white/15 shadow-inner">
              <AnimatePresence mode="wait">
                <motion.img
                  key={currentFeature.property_id}
                  src={currentFeature.image}
                  alt={currentFeature.title}
                  initial={{ opacity: 0, scale: 1.08 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.5 }}
                  className="w-full h-full object-cover"
                />
              </AnimatePresence>
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
            </div>

            {/* Residence Title & Locality */}
            <div className="space-y-1 mb-3">
              <div className="text-[11px] font-bold uppercase tracking-wider text-amber-200/90">
                {currentFeature.title}
              </div>
              <div className="text-xs font-semibold text-slate-200">
                {currentFeature.locality}, {currentFeature.city}
              </div>
            </div>

            {/* Price */}
            <div className="font-heading text-2xl font-bold text-white mb-2 tracking-tight">
              {currentFeature.price}
            </div>

            {/* Specs & Marla */}
            <div className="text-[11px] font-medium text-slate-300 tracking-wider uppercase mb-4">
              {currentFeature.beds} BED &nbsp;•&nbsp; {currentFeature.baths} BATH &nbsp;•&nbsp; {currentFeature.area}
            </div>

            {/* Action Link: "VIEW PROPERTY →" */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                if (onSelectFeaturedProperty) {
                  onSelectFeaturedProperty(currentFeature);
                } else if (onExplore) {
                  onExplore();
                }
              }}
              className="w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-bold uppercase tracking-wider text-white flex items-center justify-center gap-1.5 border border-white/20 transition-all group cursor-pointer"
            >
              <span>View Property</span>
              <ArrowRight className="w-3.5 h-3.5 text-amber-300 group-hover:translate-x-1 transition-transform" />
            </motion.button>
          </div>
        </motion.div>
      </motion.div>

      {/* Bottom Metrics Bar (Real verified values from database!) with Framer Motion */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.55 }}
        className="relative z-10 max-w-7xl mx-auto w-full pt-8 flex flex-col md:flex-row items-center justify-between gap-6 border-t border-white/10 mt-10 sm:mt-16 text-left"
      >
        <div className="flex flex-wrap items-center gap-8 sm:gap-14">
          {/* Real Total Properties from DB (e.g. 750+) */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center border border-white/15 shadow-inner">
              <Home className="w-4 h-4 text-amber-300" />
            </div>
            <div>
              <div className="font-heading text-lg sm:text-xl font-bold text-white">
                {totalProperties ? `${totalProperties}+` : "750+"}
              </div>
              <div className="text-[11px] text-slate-400">Verified Properties</div>
            </div>
          </div>

          {/* Divider */}
          <div className="hidden sm:block w-[1px] h-8 bg-white/15" />

          {/* Real Cities Count from DB (3 Cities: Islamabad, Lahore, Rawalpindi) */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center border border-white/15 shadow-inner">
              <MapPin className="w-4 h-4 text-sky-400" />
            </div>
            <div>
              <div className="font-heading text-lg sm:text-xl font-bold text-white">3 Cities</div>
              <div className="text-[11px] text-slate-400">230+ Prime Localities</div>
            </div>
          </div>

          {/* Divider */}
          <div className="hidden sm:block w-[1px] h-8 bg-white/15" />

          {/* 100% Verified DB Listings */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center border border-white/15 shadow-inner">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <div className="font-heading text-lg sm:text-xl font-bold text-white">100%</div>
              <div className="text-[11px] text-slate-400">Verified DB Listings</div>
            </div>
          </div>
        </div>

        {/* Far Right "Your next chapter starts here. ↗" */}
        <motion.div
          whileHover={{ x: 4 }}
          onClick={onExplore}
          className="flex items-center gap-2 cursor-pointer group text-slate-300 hover:text-white transition-colors"
        >
          <div className="w-10 h-[1px] bg-white/30 group-hover:w-14 transition-all" />
          <span className="text-xs sm:text-sm font-medium">Your next chapter starts here.</span>
          <ArrowUpRight className="w-4 h-4 text-amber-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
        </motion.div>
      </motion.div>
    </section>
  );
}

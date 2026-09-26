import React, { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence, useScroll, useTransform, useSpring } from "framer-motion";
import {
  Search,
  MapPin,
  Home,
  Tag,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  SlidersHorizontal,
  ChevronDown,
  Check,
} from "lucide-react";
import PropertyCard from "./PropertyCard";

function LuxuryDropdown({
  label,
  icon: Icon,
  iconColor = "text-amber-300",
  value,
  onChange,
  options,
  isOpen,
  onToggle,
  onClose,
}) {
  const dropdownRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        onClose();
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  const selected = options.find((o) => o.value === value) || options[0];

  return (
    <div ref={dropdownRef} className={`relative text-left ${isOpen ? "z-50" : "z-10"}`}>
      <button
        type="button"
        onClick={onToggle}
        className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-2xl border transition-all select-none cursor-pointer text-left ${
          isOpen
            ? "border-amber-400/70 bg-[#121c32] shadow-[0_0_20px_rgba(245,180,100,0.22)]"
            : "border-white/15 bg-[#0b1222] hover:bg-[#10182b] hover:border-amber-400/40"
        }`}
      >
        <Icon className={`w-4 h-4 ${iconColor} flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <span className="block text-[10px] font-semibold tracking-widest text-slate-400 uppercase leading-tight">
            {label}
          </span>
          <span className="block text-white font-medium text-xs truncate mt-0.5">
            {selected?.label || selected?.value}
          </span>
        </div>
        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 flex-shrink-0 ${
            isOpen ? "rotate-180 text-amber-300" : ""
          }`}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.16, ease: "easeOut" }}
            className="absolute top-[calc(100%+6px)] left-0 right-0 z-50 min-w-[210px] bg-[#0c1424] border border-amber-400/50 rounded-2xl p-1.5 shadow-[0_25px_60px_-10px_rgba(0,0,0,0.98),0_12px_35px_rgba(0,0,0,0.9),0_0_30px_rgba(245,180,100,0.2)] ring-1 ring-amber-400/25 overflow-hidden"
          >
            <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-amber-400/60 to-transparent pointer-events-none" />
            <div className="max-h-64 sm:max-h-72 overflow-y-auto space-y-0.5 custom-scrollbar">
              {options.map((opt) => {
                const isSelected = opt.value === value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value);
                      onClose();
                    }}
                    className={`w-full px-3 py-2.5 rounded-xl text-xs flex items-center justify-between transition-all cursor-pointer text-left ${
                      isSelected
                        ? "bg-amber-400/20 text-amber-300 font-semibold border border-amber-400/40 shadow-sm"
                        : "text-slate-300 hover:text-white hover:bg-[#152138]"
                    }`}
                  >
                    <span className="truncate">{opt.label}</span>
                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 ml-2" />
                    )}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function PropertyExplorer({
  isAdmin = false,
  onBookVisit,
  onAskAi,
  onEditProperty,
  onDeleteProperty,
  onTotalLoaded,
}) {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Parallax scrolling physics for ambient lights powered by Motion.dev useSpring
  const sectionRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  });
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 90,
    damping: 26,
    restDelta: 0.001,
  });
  const orb1Y = useTransform(smoothProgress, [0, 1], [-120, 120]);
  const orb2Y = useTransform(smoothProgress, [0, 1], [130, -130]);
  const orb1Scale = useTransform(smoothProgress, [0, 0.5, 1], [0.9, 1.15, 0.95]);
  const orb2Scale = useTransform(smoothProgress, [0, 0.5, 1], [1.1, 0.95, 1.05]);

  const onTotalLoadedRef = useRef(onTotalLoaded);
  useEffect(() => {
    onTotalLoadedRef.current = onTotalLoaded;
  }, [onTotalLoaded]);

  // Active Filters State
  const [city, setCity] = useState("");
  const [propType, setPropType] = useState("");
  const [purpose, setPurpose] = useState("");
  const [priceRange, setPriceRange] = useState("Any");
  const [search, setSearch] = useState("");
  const [openDropdown, setOpenDropdown] = useState(null); // "location" | "type" | "price" | "purpose" | null

  // Parse min and max price from priceRange selection
  const getPriceBounds = (range) => {
    let minPrice = "";
    let maxPrice = "";
    if (range === "Under 1 Cr") {
      maxPrice = "10000000";
    } else if (range === "1 - 3 Cr") {
      minPrice = "10000000";
      maxPrice = "30000000";
    } else if (range === "3 - 5 Cr") {
      minPrice = "30000000";
      maxPrice = "50000000";
    } else if (range === "5 - 10 Cr") {
      minPrice = "50000000";
      maxPrice = "100000000";
    } else if (range === "10+ Cr") {
      minPrice = "100000000";
    }
    return { minPrice, maxPrice };
  };

  const fetchProperties = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("limit", "12");

      if (city.trim()) params.append("city", city.trim());
      if (propType.trim()) params.append("property_type", propType.trim());
      if (purpose.trim()) params.append("purpose", purpose.trim());
      if (search.trim()) params.append("search", search.trim());

      const { minPrice, maxPrice } = getPriceBounds(priceRange);
      if (minPrice) params.append("min_price", minPrice);
      if (maxPrice) params.append("max_price", maxPrice);

      const res = await fetch(`/api/properties?${params.toString()}`);
      const data = await res.json();
      if (data.ok) {
        setProperties(data.properties || []);
        const totalCount = data.total || 0;
        setTotal(totalCount);
        setTotalPages(data.total_pages || 1);
        if (onTotalLoadedRef.current) {
          onTotalLoadedRef.current(totalCount);
        }
      }
    } catch (err) {
      console.error("Failed to load properties:", err);
    } finally {
      setLoading(false);
    }
  }, [page, city, propType, purpose, priceRange, search]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  const handleReset = () => {
    setCity("");
    setPropType("");
    setPurpose("");
    setPriceRange("Any");
    setSearch("");
    setPage(1);
  };

  const hasActiveFilters = Boolean(
    city || propType || purpose || priceRange !== "Any" || search.trim()
  );

  return (
    <section
      ref={sectionRef}
      id="properties-section"
      className="relative pt-24 sm:pt-36 lg:pt-40 pb-24 sm:pb-32 px-4 sm:px-8 w-full bg-[#090d16] text-[#FAF8F5] overflow-hidden"
    >
      {/* Pure CSS Luxury Ambient Lighting with Parallax (Complementing Hero Villa & Dusk Colors — NO Picture!) */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        {/* Warm Villa Interior Ambient Light Spill from Top with Parallax */}
        <motion.div
          style={{ y: orb1Y, scale: orb1Scale }}
          className="absolute top-0 inset-x-0 h-[480px] bg-[radial-gradient(ellipse_75%_50%_at_50%_0%,_rgba(226,183,116,0.08)_0%,_transparent_70%)]"
        />
        {/* Serene Infinity Pool Cyan Light Glow with Parallax */}
        <motion.div
          style={{ y: orb2Y, scale: orb2Scale }}
          className="absolute top-1/3 right-0 w-[550px] h-[550px] bg-[radial-gradient(circle,_rgba(56,189,248,0.04)_0%,_transparent_65%)] blur-3xl"
        />
        {/* Warm Travertine Tone on Lower Left */}
        <div className="absolute bottom-20 left-0 w-[500px] h-[500px] bg-[radial-gradient(circle,_rgba(226,183,116,0.035)_0%,_transparent_60%)] blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Architectural Transition Bridge between Hero and Curated Portfolio */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center justify-center mb-16 sm:mb-20 text-center pointer-events-none"
        >
          <div className="flex items-center gap-3 sm:gap-4 text-[10px] sm:text-xs font-mono tracking-[0.25em] sm:tracking-[0.3em] uppercase text-amber-300/80">
            <div className="w-8 sm:w-16 h-[1px] bg-gradient-to-r from-transparent via-amber-400/40 to-transparent" />
            <span className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-400/90" />
              The Verified Collection
            </span>
            <div className="w-8 sm:w-16 h-[1px] bg-gradient-to-r from-transparent via-amber-400/40 to-transparent" />
          </div>
          {/* Ambient Glowing Vertical Guide Line with Motion Pulse */}
          <div className="relative w-[1px] h-10 sm:h-14 mt-4 bg-gradient-to-b from-amber-400/30 via-white/15 to-transparent overflow-hidden">
            <motion.div
              animate={{ y: ["-100%", "200%"] }}
              transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
              className="w-full h-8 bg-gradient-to-b from-transparent via-amber-300 to-transparent"
            />
          </div>
        </motion.div>

        {/* Section Header with Motion.dev Masked Text and Smooth Entrances */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4 text-left">
          <div>
            {/* Kinetic Typography Masked Reveal */}
            <motion.h2
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
              variants={{
                hidden: {},
                visible: {
                  transition: {
                    staggerChildren: 0.12,
                    delayChildren: 0.1,
                  },
                },
              }}
              className="font-display-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-white tracking-tight flex flex-wrap gap-x-3 gap-y-1"
            >
              {["Curated", "Luxury", "Portfolio"].map((word, i) => (
                <span key={i} className="inline-block overflow-hidden py-0.5">
                  <motion.span
                    className="inline-block"
                    variants={{
                      hidden: { y: "115%", opacity: 0, rotate: 1.5 },
                      visible: {
                        y: 0,
                        opacity: 1,
                        rotate: 0,
                        transition: {
                          duration: 0.85,
                          ease: [0.16, 1, 0.3, 1],
                        },
                      },
                    }}
                  >
                    {word}
                  </motion.span>
                </span>
              ))}
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.75, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="text-slate-400 text-xs sm:text-sm mt-2 max-w-xl font-light leading-relaxed"
            >
              Browse real verified properties across Islamabad, Lahore, and Rawalpindi. Filter by locality, property type, or price.
            </motion.p>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="flex items-center gap-3"
          >
            <div className="text-xs text-slate-300 bg-white/[0.06] px-4 py-2 rounded-full border border-white/15 backdrop-blur-md shadow-sm">
              Showing <span className="text-white font-medium">{properties.length}</span> of{" "}
              <span className="text-amber-300 font-semibold">{total}</span> verified
            </div>
          </motion.div>
        </div>

        {/* LUXURY OBSIDIAN LIQUID GLASS FILTER DOCK (Matching Hero Floating Card) */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.8, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="relative z-40 rounded-3xl p-4 sm:p-5 mb-10 shadow-[0_24px_60px_-15px_rgba(0,0,0,0.85),inset_0_1px_1px_rgba(255,255,255,0.15)] border border-white/15 bg-[#0e1526]"
        >
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center relative z-20">
            {/* 1. LOCATION FILTER */}
            <div className={`md:col-span-3 ${openDropdown === "location" ? "relative z-50" : "relative z-10"}`}>
              <LuxuryDropdown
                label="Location"
                icon={MapPin}
                iconColor="text-amber-300"
                value={city}
                onChange={(val) => {
                  setCity(val);
                  setPage(1);
                }}
                options={[
                  { value: "", label: "All Cities (3 Cities)" },
                  { value: "Islamabad", label: "Islamabad (250)" },
                  { value: "Lahore", label: "Lahore (250)" },
                  { value: "Rawalpindi", label: "Rawalpindi (250)" },
                ]}
                isOpen={openDropdown === "location"}
                onToggle={() => setOpenDropdown(openDropdown === "location" ? null : "location")}
                onClose={() => setOpenDropdown(null)}
              />
            </div>

            {/* 2. PROPERTY TYPE FILTER */}
            <div className={`md:col-span-3 ${openDropdown === "type" ? "relative z-50" : "relative z-10"}`}>
              <LuxuryDropdown
                label="Property Type"
                icon={Home}
                iconColor="text-sky-400"
                value={propType}
                onChange={(val) => {
                  setPropType(val);
                  setPage(1);
                }}
                options={[
                  { value: "", label: "All Types" },
                  { value: "House", label: "House" },
                  { value: "Flat", label: "Flat / Apartment" },
                  { value: "Upper Portion", label: "Upper Portion" },
                  { value: "Lower Portion", label: "Lower Portion" },
                  { value: "Farm House", label: "Farm House" },
                ]}
                isOpen={openDropdown === "type"}
                onToggle={() => setOpenDropdown(openDropdown === "type" ? null : "type")}
                onClose={() => setOpenDropdown(null)}
              />
            </div>

            {/* 3. PRICE RANGE FILTER */}
            <div className={`md:col-span-3 ${openDropdown === "price" ? "relative z-50" : "relative z-10"}`}>
              <LuxuryDropdown
                label="Price Range"
                icon={Tag}
                iconColor="text-amber-300"
                value={priceRange}
                onChange={(val) => {
                  setPriceRange(val);
                  setPage(1);
                }}
                options={[
                  { value: "Any", label: "Any Budget" },
                  { value: "Under 1 Cr", label: "Under 1 Crore" },
                  { value: "1 - 3 Cr", label: "1 - 3 Crore" },
                  { value: "3 - 5 Cr", label: "3 - 5 Crore" },
                  { value: "5 - 10 Cr", label: "5 - 10 Crore" },
                  { value: "10+ Cr", label: "10+ Crore" },
                ]}
                isOpen={openDropdown === "price"}
                onToggle={() => setOpenDropdown(openDropdown === "price" ? null : "price")}
                onClose={() => setOpenDropdown(null)}
              />
            </div>

            {/* 4. PURPOSE FILTER */}
            <div className={`md:col-span-3 ${openDropdown === "purpose" ? "relative z-50" : "relative z-10"}`}>
              <LuxuryDropdown
                label="Purpose"
                icon={SlidersHorizontal}
                iconColor="text-emerald-400"
                value={purpose}
                onChange={(val) => {
                  setPurpose(val);
                  setPage(1);
                }}
                options={[
                  { value: "", label: "All (Sale & Rent)" },
                  { value: "For Sale", label: "For Sale" },
                  { value: "For Rent", label: "For Rent" },
                ]}
                isOpen={openDropdown === "purpose"}
                onToggle={() => setOpenDropdown(openDropdown === "purpose" ? null : "purpose")}
                onClose={() => setOpenDropdown(null)}
              />
            </div>
          </div>

          {/* Second Row: Locality Keyword Search + Actions */}
          <div className="mt-3.5 pt-3.5 border-t border-white/10 flex flex-col sm:flex-row items-center gap-3 justify-between">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                placeholder="Search specific locality (e.g. DHA Phase 6, Bahria Town, Gulberg, Sector F-7, etc.)..."
                className="w-full pl-10 pr-4 py-2.5 rounded-2xl bg-[#0b1222] border border-white/15 text-white placeholder:text-slate-400 text-xs focus:outline-none focus:border-amber-400/50 focus:bg-[#10192e] transition-all"
              />
            </div>

            <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
              {hasActiveFilters && (
                <button
                  onClick={handleReset}
                  className="px-4 py-2 rounded-full bg-white/10 hover:bg-white/20 text-xs text-slate-300 hover:text-white border border-white/15 flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
                  <span>Reset Filters</span>
                </button>
              )}

              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => {
                  setPage(1);
                  fetchProperties();
                }}
                className="px-6 py-2.5 rounded-full text-xs font-semibold text-slate-950 bg-gradient-to-r from-amber-400 via-amber-500 to-amber-600 hover:from-amber-300 hover:to-amber-500 flex items-center justify-center gap-2 cursor-pointer shadow-[0_0_20px_rgba(245,158,11,0.35)] transition-all"
              >
                <Search className="w-3.5 h-3.5 text-slate-950" />
                <span>Apply Search</span>
              </motion.button>
            </div>
          </div>
        </motion.div>

        {/* Property Cards Grid */}
        {loading && properties.length === 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-96 animate-pulse bg-white/[0.03] border border-white/10 rounded-2xl" />
            ))}
          </div>
        ) : properties.length === 0 ? (
          <div className="p-12 text-center rounded-3xl border border-white/15 bg-[#101726]/80 backdrop-blur-2xl">
            <p className="text-slate-300 text-sm mb-4 font-light">
              No properties found matching your criteria ({city || "any city"}, {propType || "any type"}, {priceRange}).
            </p>
            <button
              onClick={handleReset}
              className="px-6 py-2.5 rounded-full text-xs font-medium text-white bg-white/10 hover:bg-white/20 border border-white/20 cursor-pointer transition-all"
            >
              Clear All Filters
            </button>
          </div>
        ) : (
          <div
            className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 transition-opacity duration-200 relative z-0 ${
              loading ? "opacity-60 pointer-events-none" : "opacity-100"
            }`}
          >
            {properties.map((prop, idx) => (
              <PropertyCard
                key={prop.property_id || idx}
                property={prop}
                index={idx}
                isAdmin={isAdmin}
                onBookVisit={onBookVisit}
                onAskAi={onAskAi}
                onEdit={onEditProperty}
                onDelete={onDeleteProperty}
              />
            ))}
          </div>
        )}

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="mt-12 flex items-center justify-center gap-3">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              disabled={page <= 1}
              onClick={() => {
                setPage((p) => Math.max(1, p - 1));
                document.getElementById("properties-section")?.scrollIntoView({ behavior: "smooth" });
              }}
              className="p-2.5 rounded-full bg-white/10 border border-white/15 hover:border-white/30 disabled:opacity-30 text-slate-300 hover:text-white transition-all cursor-pointer shadow-sm"
            >
              <ChevronLeft className="w-4 h-4" />
            </motion.button>

            <div className="px-5 py-2 rounded-full bg-white/10 text-xs font-medium text-slate-300 border border-white/15 shadow-sm">
              Page <span className="text-white font-medium">{page}</span> of{" "}
              <span className="text-white font-medium">{totalPages}</span>
            </div>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              disabled={page >= totalPages}
              onClick={() => {
                setPage((p) => Math.min(totalPages, p + 1));
                document.getElementById("properties-section")?.scrollIntoView({ behavior: "smooth" });
              }}
              className="p-2.5 rounded-full bg-white/10 border border-white/15 hover:border-white/30 disabled:opacity-30 text-slate-300 hover:text-white transition-all cursor-pointer shadow-sm"
            >
              <ChevronRight className="w-4 h-4" />
            </motion.button>
          </div>
        )}
      </div>
    </section>
  );
}

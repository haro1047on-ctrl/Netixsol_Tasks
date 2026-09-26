import React from "react";
import { motion } from "framer-motion";
import { Bed, Bath, Maximize2, MapPin, Calendar, Sparkles, Edit3, Trash2, ArrowRight } from "lucide-react";

// Curated Pakistani luxury real estate architectural imagery
const PROPERTY_IMAGES = [
  "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1600573472550-8090b5e0745e?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=800&q=80",
  "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=800&q=80",
];

export function formatPKR(price) {
  const num = Number(price);
  if (isNaN(num)) return `PKR ${price}`;
  if (num >= 10000000) {
    const crore = (num / 10000000).toFixed(2);
    return `PKR ${crore} Cr`;
  }
  if (num >= 100000) {
    const lakh = (num / 100000).toFixed(1);
    return `PKR ${lakh} Lakh`;
  }
  return `PKR ${num.toLocaleString()}`;
}

// Convert real database area_marla & area_sqft into standard Pakistani real estate units
export function formatRealSize(area_marla, area_sqft) {
  const m = Number(area_marla);
  const s = Number(area_sqft);

  if (!isNaN(m) && m > 0) {
    if (m >= 20) {
      const kanal = m / 20;
      if (m % 20 === 0) {
        return `${kanal} Kanal (${m} Marla)`;
      } else {
        return `${kanal.toFixed(1)} Kanal (${m} Marla)`;
      }
    }
    const formatted = m % 1 === 0 ? m.toString() : m.toFixed(1);
    return `${formatted} Marla`;
  }

  if (!isNaN(s) && s > 0) {
    return `${Math.round(s).toLocaleString()} sqft`;
  }

  return "Size on request";
}

export function formatAreaSqft(area_sqft, area_marla) {
  const s = Number(area_sqft);
  if (!isNaN(s) && s > 0) {
    return `${Math.round(s).toLocaleString()} sqft`;
  }
  const m = Number(area_marla);
  if (!isNaN(m) && m > 0) {
    return `${Math.round(m * 225).toLocaleString()} sqft`;
  }
  return null;
}

export default function PropertyCard({
  property,
  index = 0,
  isAdmin = false,
  onBookVisit,
  onAskAi,
  onEdit,
  onDelete,
}) {
  const imgUrl = PROPERTY_IMAGES[index % PROPERTY_IMAGES.length];
  const realSizeLabel = formatRealSize(property.area_marla, property.area_sqft);
  const realSqftLabel = formatAreaSqft(property.area_sqft, property.area_marla);

  const isForRent = (property.purpose || "").toLowerCase().includes("rent");

  return (
    <motion.div
      initial={{ opacity: 0, y: 22, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.45,
        delay: Math.min((index % 12) * 0.035, 0.3),
        ease: [0.16, 1, 0.3, 1],
      }}
      whileHover={{ y: -6, transition: { duration: 0.25, ease: "easeOut" } }}
      className="overflow-hidden flex flex-col group rounded-2xl bg-[#0e1422]/85 backdrop-blur-xl border border-white/10 hover:border-white/25 shadow-[0_16px_36px_-10px_rgba(0,0,0,0.6)] hover:shadow-[0_24px_50px_-10px_rgba(0,0,0,0.8),0_0_25px_rgba(245,180,100,0.06)]"
    >
      {/* Cover Image with Glass Badges */}
      <div className="relative h-52 sm:h-56 w-full overflow-hidden bg-slate-950">
        <img
          src={imgUrl}
          alt={property.locality}
          className="w-full h-full object-cover group-hover:scale-106 transition-transform duration-700 ease-out"
          loading="lazy"
        />
        {/* Subtle Bottom Image Gradient Overlay for Price Contrast while keeping image fully bright */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0e1422] via-transparent to-transparent opacity-90 pointer-events-none z-10" />

        {/* Top Badges */}
        <div className="absolute top-3 left-3 flex flex-wrap items-center gap-1.5 z-20">
          <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-[#060a14]/90 backdrop-blur-md text-slate-100 border border-white/20 shadow-md">
            {property.property_type || "House"}
          </span>
          <span
            className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider backdrop-blur-md shadow-md border ${
              isForRent
                ? "bg-[#060a14]/90 text-sky-300 border-sky-400/60 shadow-[0_2px_12px_rgba(0,0,0,0.7)]"
                : "bg-[#060a14]/90 text-amber-300 border-amber-400/60 shadow-[0_2px_12px_rgba(0,0,0,0.7)]"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full mr-1.5 flex-shrink-0 ${
                isForRent
                  ? "bg-sky-400 shadow-[0_0_6px_rgba(56,189,248,0.8)]"
                  : "bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.8)]"
              }`}
            />
            {property.purpose || "For Sale"}
          </span>
        </div>

        {/* Property ID */}
        <div className="absolute top-3 right-3 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium text-slate-200 bg-[#060a14]/90 backdrop-blur-md border border-white/20 shadow-md z-20">
          {property.property_id}
        </div>

        {/* Price & Real Marla/Kanal Size Tag Overlay */}
        <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between z-20 gap-2">
          <div className="text-xl sm:text-2xl font-heading font-semibold text-white drop-shadow-md tracking-tight">
            {formatPKR(property.price)}
          </div>
          <div className="text-xs font-medium text-amber-300 bg-black/70 backdrop-blur-md border border-amber-400/30 px-2.5 py-1 rounded-full whitespace-nowrap shadow-sm">
            {realSizeLabel}
          </div>
        </div>
      </div>

      {/* Content Body */}
      <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between text-left">
        <div>
          {/* Locality & City */}
          <div className="flex items-center gap-1.5 text-white text-xs font-medium mb-1 truncate">
            <MapPin className="w-3.5 h-3.5 text-amber-300 flex-shrink-0" />
            <span className="truncate text-white font-medium">{property.locality}, {property.city}</span>
          </div>

          <p className="text-xs text-slate-400 mb-4 line-clamp-1 font-light">
            {property.location || `${realSizeLabel} ${property.property_type} in ${property.locality}`}
          </p>

          {/* Real Specs Grid */}
          <div className="grid grid-cols-3 gap-2 py-2 px-3 rounded-xl border border-white/10 bg-white/[0.04] text-xs text-slate-300 mb-2">
            <div className="flex items-center gap-1.5" title="Real Bed Count">
              <Bed className="w-3.5 h-3.5 text-amber-300/90" />
              <span>{property.bedrooms ? `${property.bedrooms} Beds` : "Studio"}</span>
            </div>
            <div className="flex items-center gap-1.5" title="Real Bath Count">
              <Bath className="w-3.5 h-3.5 text-amber-300/90" />
              <span>{property.baths ? `${property.baths} Baths` : "1 Bath"}</span>
            </div>
            <div className="flex items-center gap-1.5 truncate" title="Real Plot Size">
              <Maximize2 className="w-3.5 h-3.5 text-amber-300/90 flex-shrink-0" />
              <span className="truncate">{realSizeLabel}</span>
            </div>
          </div>

          {/* Covered Area */}
          {realSqftLabel && (
            <div className="flex items-center justify-between text-[11px] text-slate-400 px-1 mb-4 font-light">
              <span>Covered Area:</span>
              <span className="text-slate-200 font-mono font-medium">{realSqftLabel}</span>
            </div>
          )}
        </div>

        {/* Action Buttons - Lively, Animated CTA */}
        <div className="space-y-2 pt-3 border-t border-white/10">
          <div className="flex items-center gap-2">
            <motion.button
              whileHover={{ scale: 1.03, y: -1.5 }}
              whileTap={{ scale: 0.96 }}
              onClick={() => onBookVisit(property)}
              className="relative flex-1 py-2.5 px-3.5 rounded-full bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 group/btn cursor-pointer shadow-[0_4px_18px_rgba(245,180,100,0.35)] hover:shadow-[0_6px_25px_rgba(245,180,100,0.6)] transition-all overflow-hidden"
            >
              {/* Dynamic Shimmer Light Reflection Sweep on Hover */}
              <div className="absolute inset-0 -translate-x-full group-hover/btn:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/50 to-transparent pointer-events-none" />

              {/* Lively Pulse Indicator Dot */}
              <span className="relative flex h-2 w-2 flex-shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-slate-950 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-slate-950" />
              </span>

              <Calendar className="w-3.5 h-3.5 text-slate-950 group-hover/btn:rotate-12 group-hover/btn:scale-125 transition-transform duration-300 flex-shrink-0" />
              <span className="tracking-wide">Book Visit</span>
              <ArrowRight className="w-3 h-3 text-slate-950/80 group-hover/btn:translate-x-1 transition-transform flex-shrink-0" />
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.06, y: -1.5 }}
              whileTap={{ scale: 0.94 }}
              onClick={() => onAskAi(property)}
              className="px-3.5 py-2.5 rounded-full bg-white/[0.08] hover:bg-amber-400/20 border border-white/20 hover:border-amber-400/50 text-amber-300 hover:text-amber-200 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
              title="Consult AI Assistant about this property"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300 group-hover:rotate-12 transition-transform" />
              <span>AI</span>
            </motion.button>
          </div>

          {/* Admin Edit / Delete Actions */}
          {isAdmin && (
            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                onClick={() => onEdit(property)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                title="Edit Property"
              >
                <Edit3 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onDelete(property)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-red-300 hover:bg-red-500/10 transition-colors cursor-pointer"
                title="Delete Property"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

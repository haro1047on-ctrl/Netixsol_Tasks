import React, { useState, useEffect, useCallback } from "react";
import { Plus, Edit, Trash2, Calendar, Users, Building, CheckCircle, Clock, XCircle, Search, RefreshCw, AlertCircle, ArrowUpRight } from "lucide-react";
import { formatPKR } from "./PropertyCard";

export default function AdminPortal({ onRefreshStats }) {
  const [activeAdminTab, setActiveAdminTab] = useState("properties"); // "properties" | "schedules" | "leads"
  
  // Properties state
  const [properties, setProperties] = useState([]);
  const [totalProps, setTotalProps] = useState(0);
  const [search, setSearch] = useState("");
  const [propPage, setPropPage] = useState(1);
  const [loadingProps, setLoadingProps] = useState(false);

  // Appointments state
  const [appointments, setAppointments] = useState([]);
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState({});
  const [loadingCRM, setLoadingCRM] = useState(false);

  // Modals state
  const [showAddModal, setShowAddModal] = useState(false);
  const [editProperty, setEditProperty] = useState(null);
  const [rescheduleAppt, setRescheduleAppt] = useState(null);
  const [cancelAppt, setCancelAppt] = useState(null);

  // Form inputs for Add/Edit
  const [formProp, setFormProp] = useState({
    property_id: "",
    property_type: "House",
    purpose: "For Sale",
    city: "Lahore",
    locality: "DHA Phase 6",
    location: "DHA Phase 6, Lahore",
    price: 28500000,
    area_marla: 5,
    bedrooms: 3,
    baths: 3,
    agent: "Ahmed Raza (Sahi RealEstate)",
  });

  // Reschedule Form
  const [newDate, setNewDate] = useState("Tomorrow");
  const [newTime, setNewTime] = useState("4:00 PM");
  const [reschedNotes, setReschedNotes] = useState("");
  const [cancelReason, setCancelReason] = useState("");

  const fetchProperties = useCallback(async () => {
    setLoadingProps(true);
    try {
      const res = await fetch(`/api/properties?page=${propPage}&limit=10&search=${encodeURIComponent(search)}`);
      const data = await res.json();
      if (data.ok) {
        setProperties(data.properties || []);
        setTotalProps(data.total || 0);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingProps(false);
    }
  }, [propPage, search]);

  const fetchCRMData = useCallback(async () => {
    setLoadingCRM(true);
    try {
      const [apptsRes, leadsRes, statsRes] = await Promise.all([
        fetch("/api/crm/appointments").then((r) => r.json()),
        fetch("/api/crm/leads").then((r) => r.json()),
        fetch("/api/crm/stats").then((r) => r.json()),
      ]);
      if (apptsRes.ok) setAppointments(apptsRes.appointments || []);
      if (leadsRes.ok) setLeads(leadsRes.leads || []);
      if (statsRes.ok) setStats(statsRes.stats || {});
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCRM(false);
    }
  }, []);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  useEffect(() => {
    fetchCRMData();
  }, [fetchCRMData]);

  // Handle Add Property
  const handleSaveAdd = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/properties", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formProp),
      });
      const data = await res.json();
      if (data.ok) {
        setShowAddModal(false);
        fetchProperties();
        fetchCRMData();
        if (onRefreshStats) onRefreshStats();
      } else {
        alert(data.error || "Failed to add property");
      }
    } catch (err) {
      alert("Error adding property: " + err.message);
    }
  };

  // Handle Edit Property
  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editProperty) return;
    try {
      const res = await fetch(`/api/properties/${editProperty.property_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editProperty),
      });
      const data = await res.json();
      if (data.ok) {
        setEditProperty(null);
        fetchProperties();
      } else {
        alert(data.error || "Failed to edit property");
      }
    } catch (err) {
      alert("Error updating property: " + err.message);
    }
  };

  // Handle Delete Property
  const handleDelete = async (pid) => {
    if (!window.confirm(`Are you sure you want to delete property ${pid}?`)) return;
    try {
      await fetch(`/api/properties/${pid}`, { method: "DELETE" });
      fetchProperties();
      fetchCRMData();
    } catch (err) {
      alert("Error deleting: " + err.message);
    }
  };

  // Handle Reschedule Appointment
  const handleRescheduleSubmit = async (e) => {
    e.preventDefault();
    if (!rescheduleAppt) return;
    try {
      await fetch(`/api/crm/appointments/${rescheduleAppt.appointment_id}/reschedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date_str: newDate,
          time_str: newTime,
          notes: reschedNotes || "Rescheduled via Admin CRM",
        }),
      });
      setRescheduleAppt(null);
      fetchCRMData();
    } catch (err) {
      alert("Error rescheduling: " + err.message);
    }
  };

  // Handle Cancel Appointment
  const handleCancelSubmit = async (e) => {
    e.preventDefault();
    if (!cancelAppt) return;
    try {
      await fetch(`/api/crm/appointments/${cancelAppt.appointment_id}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: cancelReason || "Cancelled by admin" }),
      });
      setCancelAppt(null);
      fetchCRMData();
    } catch (err) {
      alert("Error cancelling: " + err.message);
    }
  };

  return (
    <div className="py-8 px-4 sm:px-8 max-w-7xl mx-auto">
      {/* Top Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="glass-panel p-4 bg-slate-900/80 rounded-2xl border border-white/10 flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
            <Building className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xl font-heading font-extrabold text-white">{stats.total_properties || totalProps}</div>
            <div className="text-xs text-slate-400">Total Properties</div>
          </div>
        </div>

        <div className="glass-panel p-4 bg-slate-900/80 rounded-2xl border border-white/10 flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-cyan-500/15 text-cyan-400 border border-cyan-500/20">
            <Calendar className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xl font-heading font-extrabold text-white">{stats.total_appointments || appointments.length}</div>
            <div className="text-xs text-slate-400">Total Visits Booked</div>
          </div>
        </div>

        <div className="glass-panel p-4 bg-slate-900/80 rounded-2xl border border-white/10 flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-amber-500/15 text-amber-400 border border-amber-500/20">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xl font-heading font-extrabold text-white">{stats.scheduled_appointments || 0}</div>
            <div className="text-xs text-slate-400">Scheduled / Active</div>
          </div>
        </div>

        <div className="glass-panel p-4 bg-slate-900/80 rounded-2xl border border-white/10 flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-purple-500/15 text-purple-400 border border-purple-500/20">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xl font-heading font-extrabold text-white">{stats.total_leads || leads.length}</div>
            <div className="text-xs text-slate-400">CRM Client Leads</div>
          </div>
        </div>
      </div>

      {/* Admin Navigation Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-white/10">
        <div className="flex bg-slate-900/80 p-1 rounded-xl border border-white/10">
          <button
            onClick={() => setActiveAdminTab("properties")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeAdminTab === "properties"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20"
                : "text-slate-300 hover:text-white"
            }`}
          >
            Properties Management ({totalProps})
          </button>
          <button
            onClick={() => setActiveAdminTab("schedules")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeAdminTab === "schedules"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20"
                : "text-slate-300 hover:text-white"
            }`}
          >
            CRM Visit Schedules ({appointments.length})
          </button>
          <button
            onClick={() => setActiveAdminTab("leads")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeAdminTab === "leads"
                ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20"
                : "text-slate-300 hover:text-white"
            }`}
          >
            Client Leads Pipeline ({leads.length})
          </button>
        </div>

        {activeAdminTab === "properties" && (
          <button
            onClick={() => setShowAddModal(true)}
            className="btn-primary text-xs py-2 px-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-bold border-amber-400/30"
          >
            <Plus className="w-4 h-4" />
            Add New Property
          </button>
        )}
      </div>

      {/* Tab 1: Properties Management */}
      {activeAdminTab === "properties" && (
        <div className="glass-panel p-5 bg-slate-900/80 rounded-2xl border border-white/10 overflow-hidden">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPropPage(1); }}
                placeholder="Filter listings by ID, locality, city..."
                className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-950/70 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-500"
              />
            </div>
            <button
              onClick={fetchProperties}
              className="btn-secondary text-xs py-1.5 px-3 rounded-lg"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/70 text-[11px] uppercase tracking-wider text-slate-400 border-b border-white/10">
                <tr>
                  <th className="p-3">ID</th>
                  <th className="p-3">Type / Purpose</th>
                  <th className="p-3">Locality & City</th>
                  <th className="p-3">Price</th>
                  <th className="p-3">Area / Beds</th>
                  <th className="p-3">Assigned Agent</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {properties.map((p) => (
                  <tr key={p.property_id} className="hover:bg-white/5 transition-colors">
                    <td className="p-3 font-mono font-bold text-amber-400">{p.property_id}</td>
                    <td className="p-3">
                      <span className="font-semibold text-white">{p.property_type}</span>
                      <span className="text-[10px] block text-slate-400">{p.purpose}</span>
                    </td>
                    <td className="p-3">
                      <div className="text-white font-medium">{p.locality}</div>
                      <div className="text-[10px] text-slate-400">{p.city}</div>
                    </td>
                    <td className="p-3 font-bold text-emerald-400">{formatPKR(p.price)}</td>
                    <td className="p-3">
                      <div>{p.area_marla} Marla</div>
                      <div className="text-[10px] text-slate-400">{p.bedrooms} Beds • {p.baths} Baths</div>
                    </td>
                    <td className="p-3 text-slate-300 truncate max-w-[140px]">{p.agent}</td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setEditProperty({ ...p })}
                          className="p-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 transition-colors"
                          title="Edit Property"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(p.property_id)}
                          className="p-1.5 rounded-lg bg-red-500/15 hover:bg-red-500/25 text-red-300 transition-colors"
                          title="Delete Property"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
            <span>Page {propPage}</span>
            <div className="flex items-center gap-2">
              <button
                disabled={propPage <= 1}
                onClick={() => setPropPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 rounded bg-slate-800 disabled:opacity-30 hover:bg-slate-700"
              >
                Previous
              </button>
              <button
                disabled={properties.length < 10}
                onClick={() => setPropPage((p) => p + 1)}
                className="px-3 py-1 rounded bg-slate-800 disabled:opacity-30 hover:bg-slate-700"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: CRM Visit Schedules */}
      {activeAdminTab === "schedules" && (
        <div className="glass-panel p-5 bg-slate-900/80 rounded-2xl border border-white/10 overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-heading font-bold text-base text-white">Client Site Visit Appointments</h3>
            <button onClick={fetchCRMData} className="btn-secondary text-xs py-1.5 px-3">
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Schedules
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/70 text-[11px] uppercase tracking-wider text-slate-400 border-b border-white/10">
                <tr>
                  <th className="p-3">Appointment ID</th>
                  <th className="p-3">Client Details</th>
                  <th className="p-3">Target Property</th>
                  <th className="p-3">Date & Time</th>
                  <th className="p-3">Assigned Consultant</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {appointments.map((a) => (
                  <tr key={a.appointment_id} className="hover:bg-white/5 transition-colors">
                    <td className="p-3 font-mono text-cyan-400 font-semibold">{a.appointment_id}</td>
                    <td className="p-3">
                      <div className="text-white font-bold">{a.client_name}</div>
                      <div className="text-[10px] text-slate-400">{a.client_phone}</div>
                    </td>
                    <td className="p-3">
                      <div className="text-white font-medium truncate max-w-[180px]">{a.property_title}</div>
                      <div className="text-[10px] font-mono text-slate-400">{a.property_id}</div>
                    </td>
                    <td className="p-3">
                      <div className="text-emerald-400 font-semibold">{a.date_str}</div>
                      <div className="text-[10px] text-slate-400">{a.time_str}</div>
                    </td>
                    <td className="p-3 text-slate-300">{a.agent_name}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                        a.status === "scheduled"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : a.status === "rescheduled"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          : "bg-red-500/20 text-red-300 border border-red-500/30"
                      }`}>
                        {a.status}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => {
                            setRescheduleAppt(a);
                            setNewDate(a.date_str || "Tomorrow");
                            setNewTime(a.time_str || "4:00 PM");
                          }}
                          className="px-2 py-1 rounded bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 text-[11px] font-semibold"
                        >
                          Reschedule
                        </button>
                        {a.status !== "cancelled" && (
                          <button
                            onClick={() => setCancelAppt(a)}
                            className="px-2 py-1 rounded bg-red-500/15 hover:bg-red-500/25 text-red-300 text-[11px] font-semibold"
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: CRM Leads Pipeline */}
      {activeAdminTab === "leads" && (
        <div className="glass-panel p-5 bg-slate-900/80 rounded-2xl border border-white/10 overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-heading font-bold text-base text-white">Client Inquiry & Lead Pipeline</h3>
            <button onClick={fetchCRMData} className="btn-secondary text-xs py-1.5 px-3">
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Leads
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/70 text-[11px] uppercase tracking-wider text-slate-400 border-b border-white/10">
                <tr>
                  <th className="p-3">Lead ID</th>
                  <th className="p-3">Client Name</th>
                  <th className="p-3">Contact</th>
                  <th className="p-3">City / Locality</th>
                  <th className="p-3">Budget</th>
                  <th className="p-3">Stage</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {leads.map((l) => (
                  <tr key={l.lead_id} className="hover:bg-white/5 transition-colors">
                    <td className="p-3 font-mono text-purple-400">{l.lead_id}</td>
                    <td className="p-3 font-bold text-white">{l.client_name}</td>
                    <td className="p-3">
                      <div>{l.phone}</div>
                      <div className="text-[10px] text-slate-400">{l.email}</div>
                    </td>
                    <td className="p-3">{l.city || "Lahore"}</td>
                    <td className="p-3 font-semibold text-emerald-400">{l.budget || "Not Specified"}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                        {l.stage || "Qualified"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal: Add Property */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="glass-panel p-6 max-w-lg w-full bg-slate-900 border border-white/20 rounded-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="font-heading font-bold text-lg text-white mb-4">Add Verified Property</h3>
            <form onSubmit={handleSaveAdd} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Property Type</label>
                  <select
                    value={formProp.property_type}
                    onChange={(e) => setFormProp({ ...formProp, property_type: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  >
                    <option value="House">House</option>
                    <option value="Flat">Flat</option>
                    <option value="Upper Portion">Upper Portion</option>
                    <option value="Lower Portion">Lower Portion</option>
                    <option value="Farm House">Farm House</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Purpose</label>
                  <select
                    value={formProp.purpose}
                    onChange={(e) => setFormProp({ ...formProp, purpose: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  >
                    <option value="For Sale">For Sale</option>
                    <option value="For Rent">For Rent</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">City</label>
                  <select
                    value={formProp.city}
                    onChange={(e) => setFormProp({ ...formProp, city: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  >
                    <option value="Lahore">Lahore</option>
                    <option value="Islamabad">Islamabad</option>
                    <option value="Rawalpindi">Rawalpindi</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Locality</label>
                  <input
                    type="text"
                    required
                    value={formProp.locality}
                    onChange={(e) => setFormProp({ ...formProp, locality: e.target.value, location: `${e.target.value}, ${formProp.city}` })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Price (PKR)</label>
                  <input
                    type="number"
                    required
                    value={formProp.price}
                    onChange={(e) => setFormProp({ ...formProp, price: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Area Marla</label>
                  <input
                    type="number"
                    step="0.5"
                    required
                    value={formProp.area_marla}
                    onChange={(e) => setFormProp({ ...formProp, area_marla: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Bedrooms</label>
                  <input
                    type="number"
                    value={formProp.bedrooms}
                    onChange={(e) => setFormProp({ ...formProp, bedrooms: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Baths</label>
                  <input
                    type="number"
                    value={formProp.baths}
                    onChange={(e) => setFormProp({ ...formProp, baths: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Agent Name</label>
                <input
                  type="text"
                  value={formProp.agent}
                  onChange={(e) => setFormProp({ ...formProp, agent: e.target.value })}
                  className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary text-xs bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold"
                >
                  Add Property
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Edit Property */}
      {editProperty && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="glass-panel p-6 max-w-lg w-full bg-slate-900 border border-white/20 rounded-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="font-heading font-bold text-lg text-white mb-4">Edit Property {editProperty.property_id}</h3>
            <form onSubmit={handleSaveEdit} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Price (PKR)</label>
                  <input
                    type="number"
                    required
                    value={editProperty.price}
                    onChange={(e) => setEditProperty({ ...editProperty, price: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Area Marla</label>
                  <input
                    type="number"
                    step="0.5"
                    value={editProperty.area_marla}
                    onChange={(e) => setEditProperty({ ...editProperty, area_marla: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Locality</label>
                  <input
                    type="text"
                    value={editProperty.locality}
                    onChange={(e) => setEditProperty({ ...editProperty, locality: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Agent</label>
                  <input
                    type="text"
                    value={editProperty.agent}
                    onChange={(e) => setEditProperty({ ...editProperty, agent: e.target.value })}
                    className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setEditProperty(null)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary text-xs bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Reschedule Appointment */}
      {rescheduleAppt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="glass-panel p-6 max-w-md w-full bg-slate-900 border border-white/20 rounded-2xl">
            <h3 className="font-heading font-bold text-base text-white mb-2">Reschedule Visit</h3>
            <p className="text-xs text-slate-400 mb-4">
              Reschedule appointment for <span className="text-white font-semibold">{rescheduleAppt.client_name}</span>.
            </p>
            <form onSubmit={handleRescheduleSubmit} className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">New Date</label>
                <input
                  type="text"
                  required
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">New Time</label>
                <input
                  type="text"
                  required
                  value={newTime}
                  onChange={(e) => setNewTime(e.target.value)}
                  className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Reason / Notes</label>
                <input
                  type="text"
                  value={reschedNotes}
                  onChange={(e) => setReschedNotes(e.target.value)}
                  className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/10">
                <button type="button" onClick={() => setRescheduleAppt(null)} className="btn-secondary text-xs">
                  Cancel
                </button>
                <button type="submit" className="btn-primary text-xs">
                  Confirm Reschedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Cancel Appointment */}
      {cancelAppt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="glass-panel p-6 max-w-md w-full bg-slate-900 border border-white/20 rounded-2xl">
            <h3 className="font-heading font-bold text-base text-white mb-2">Cancel Appointment</h3>
            <p className="text-xs text-slate-400 mb-4">
              Are you sure you want to cancel the appointment for <span className="text-white font-semibold">{cancelAppt.client_name}</span>?
            </p>
            <form onSubmit={handleCancelSubmit} className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">Cancellation Reason</label>
                <input
                  type="text"
                  required
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="e.g. Client requested cancellation"
                  className="w-full p-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/10">
                <button type="button" onClick={() => setCancelAppt(null)} className="btn-secondary text-xs">
                  Back
                </button>
                <button type="submit" className="px-4 py-2 rounded-xl bg-red-500 hover:bg-red-400 text-white text-xs font-semibold">
                  Confirm Cancellation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

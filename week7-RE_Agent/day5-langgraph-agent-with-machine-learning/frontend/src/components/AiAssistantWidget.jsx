import React, { useState, useEffect, useRef } from "react";
import {
  X, Sparkles, Send, Mic, MicOff, PhoneCall, PhoneOff, MessageSquare,
  Volume2, Maximize2, Minimize2, ArrowRight, Bot, User, CheckCircle2,
  AlertTriangle, Radio, RefreshCw, ChevronDown, ChevronUp, Settings2
} from "lucide-react";
import Vapi from "@vapi-ai/web";
import { formatPKR } from "./PropertyCard";

export default function AiAssistantWidget({
  isOpen,
  onClose,
  initialQuery = "",
  onBookVisit,
}) {
  const [activeMode, setActiveMode] = useState("chat"); // "chat" | "voice"
  const [voiceSubMode, setVoiceSubMode] = useState("vapi"); // "vapi" | "browser"
  const [isExpanded, setIsExpanded] = useState(false);

  // Chat State
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Assalam-o-Alaikum! Main RealEstate Hub ka AI Consultant hoon. Bataiye, aap ghar dekh rahe hain ya flat? Aap kis city aur budget mein property chahte hain?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputText, setInputText] = useState(initialQuery || "");
  const [sending, setSending] = useState(false);
  const [sessionId] = useState(() => `web-session-${Math.random().toString(36).substring(2, 10)}`);
  const chatScrollRef = useRef(null);

  // Voice State
  const [isCalling, setIsCalling] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("Ready to connect");
  const [isMuted, setIsMuted] = useState(false);
  const [assistantVolume, setAssistantVolume] = useState(0); // Assistant voice volume
  const [userMicLevel, setUserMicLevel] = useState(0); // Live user microphone level
  const [micWarning, setMicWarning] = useState("");
  const [transcripts, setTranscripts] = useState([]);
  const [voiceMessages, setVoiceMessages] = useState([]); // Blank initially for voice mode
  const [isBrowserListening, setIsBrowserListening] = useState(false);
  const [browserSpeechText, setBrowserSpeechText] = useState("");
  const [liveVapiTranscript, setLiveVapiTranscript] = useState("");
  const [browserLang, setBrowserLang] = useState("en-US"); // "en-US" (Auto/UrduLish) or "ur-PK"
  const [audioDevices, setAudioDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [isTestingMic, setIsTestingMic] = useState(false);
  const [showAudioSettings, setShowAudioSettings] = useState(false);

  const vapiRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const audioContextRef = useRef(null);
  const micCheckStreamRef = useRef(null);
  const analyserIntervalRef = useRef(null);
  const speechTimeoutRef = useRef(null);

  useEffect(() => {
    if (initialQuery) {
      setInputText(initialQuery);
    }
  }, [initialQuery]);

  // Keep chat scrolled to bottom as messages or speech streams in
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages, voiceMessages, transcripts, browserSpeechText, liveVapiTranscript]);

  // Enumerate microphones
  const refreshAudioDevices = async () => {
    try {
      if (!navigator.mediaDevices?.enumerateDevices) return;
      const devices = await navigator.mediaDevices.enumerateDevices();
      const inputs = devices.filter((d) => d.kind === "audioinput");
      setAudioDevices(inputs);
      if (inputs.length > 0 && !selectedDeviceId) {
        const preferred = inputs.find((d) => {
          const l = d.label.toLowerCase();
          return (l.includes("array") || l.includes("mic")) && !l.includes("stereo");
        }) || inputs[0];
        if (preferred) setSelectedDeviceId(preferred.deviceId);
      }
    } catch (e) {
      console.warn("Could not enumerate audio devices:", e);
    }
  };

  useEffect(() => {
    refreshAudioDevices();
  }, [activeMode]);

  // Clean up any test mic streams
  const stopMicTestStream = () => {
    if (analyserIntervalRef.current) {
      clearInterval(analyserIntervalRef.current);
      analyserIntervalRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch (e) { }
      audioContextRef.current = null;
    }
    if (micCheckStreamRef.current) {
      try {
        micCheckStreamRef.current.getTracks().forEach((t) => t.stop());
      } catch (e) { }
      micCheckStreamRef.current = null;
    }
  };

  // Hardware Mic Test
  const testMicrophoneInput = async () => {
    if (isTestingMic) {
      stopMicTestStream();
      setIsTestingMic(false);
      setUserMicLevel(0);
      setMicWarning("");
      return;
    }

    stopMicTestStream();
    setIsTestingMic(true);
    setMicWarning("Listening to microphone... Speak or tap near your laptop mic now");

    try {
      const constraints = {
        audio: selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : true,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      micCheckStreamRef.current = stream;

      refreshAudioDevices();

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioCtx();
      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.2;

      const muteGain = audioCtx.createGain();
      muteGain.gain.value = 0;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);
      analyser.connect(muteGain);
      muteGain.connect(audioCtx.destination);

      const timeData = new Uint8Array(analyser.fftSize);
      let checks = 0;
      let heardSound = false;

      analyserIntervalRef.current = setInterval(() => {
        analyser.getByteTimeDomainData(timeData);
        let sumDeviation = 0;
        for (let i = 0; i < timeData.length; i++) {
          sumDeviation += Math.abs(timeData[i] - 128);
        }
        const avgDev = sumDeviation / timeData.length;
        const norm = Math.min(avgDev / 10, 1);
        setUserMicLevel(norm);

        if (norm > 0.04) {
          heardSound = true;
          setMicWarning("Sound detected! Microphone is active and receiving audio.");
        }
        checks++;

        if (checks > 70) {
          stopMicTestStream();
          setIsTestingMic(false);
          setUserMicLevel(0);
          if (heardSound) {
            setMicWarning("Microphone is working properly!");
            setTimeout(() => setMicWarning(""), 3500);
          } else {
            setMicWarning("Microphone signal is silent (0%). Select another input device below.");
          }
        }
      }, 100);
    } catch (err) {
      stopMicTestStream();
      setIsTestingMic(false);
      setMicWarning(`Microphone error: ${err.message || "Permission denied"}`);
    }
  };

  // Handle Send Chat
  const handleSendMessage = async (textToSend) => {
    const text = (textToSend || inputText).trim();
    if (!text || sending) return;

    setInputText("");
    const userMsg = {
      role: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    if (activeMode === "voice") {
      setVoiceMessages((prev) => [...prev, userMsg]);
    } else {
      setMessages((prev) => [...prev, userMsg]);
    }
    setSending(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });
      const data = await res.json();

      if (data.ok) {
        const assistantMsg = {
          role: "assistant",
          text: data.reply,
          properties: data.recommended_properties || [],
          intent: data.intent,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        if (activeMode === "voice") {
          setVoiceMessages((prev) => [...prev, assistantMsg]);
        } else {
          setMessages((prev) => [...prev, assistantMsg]);
        }
        return data.reply;
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSending(false);
    }
    return null;
  };

  // =========================================================================
  // 1. VAPI WEBRTC CLOUD CALL
  // =========================================================================
  const startVapiCall = async () => {
    stopMicTestStream();
    setIsCalling(true);
    setVoiceMessages([]); // Clean blank slate before agent speaks first message
    setLiveVapiTranscript("");
    setVoiceStatus("Connecting to Deepgram Nova-3 Urdu AI...");
    setMicWarning("");

    try {
      try {
        const testStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        testStream.getTracks().forEach((t) => t.stop());
      } catch (e) {
        throw new Error("Microphone permission denied. Please allow microphone access in your browser.");
      }

      let assistantId = "5b8807b3-1e6d-4a38-b1ba-25715f349899";
      let vapiPublicKey = "9efb9bb5-3fcf-439e-becf-f98742ab98d4";

      try {
        const res = await fetch("/api/health");
        if (res.ok) {
          const healthData = await res.json();
          if (healthData.vapi_assistant_id) assistantId = healthData.vapi_assistant_id;
          if (healthData.vapi_public_key) vapiPublicKey = healthData.vapi_public_key;
        }
      } catch (e) { }

      const vapi = new Vapi(vapiPublicKey);
      vapiRef.current = vapi;

      vapi.on("call-start", () => {
        setVoiceStatus("Call connected — bolna shuru kijiye");
      });

      vapi.on("speech-start", () => {
        setVoiceStatus("Listening to you (Deepgram Nova-3)...");
      });

      vapi.on("speech-end", () => {
        setVoiceStatus("Agent analyzing your request...");
      });

      vapi.on("volume-level", (volume) => {
        setAssistantVolume(volume);
      });

      vapi.on("local-volume-level", (level) => {
        setUserMicLevel(level);
        if (level > 0.04) {
          setMicWarning("");
        }
      });

      // Stream transcripts into voice chat: merge consecutive speech from same speaker
      vapi.on("message", (msg) => {
        if (msg.type === "transcript") {
          const role = msg.role === "assistant" ? "assistant" : "user";
          if (msg.transcriptType === "partial") {
            setLiveVapiTranscript(msg.transcript);
          } else {
            setLiveVapiTranscript("");
            const text = (msg.transcript || "").trim();
            if (text) {
              const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
              setVoiceMessages((prev) => {
                if (prev.length === 0) {
                  return [{ role, text, timestamp: time, isVoice: true }];
                }
                const last = prev[prev.length - 1];
                if (last.text === text) {
                  return prev;
                }
                // If same speaker continues talking, combine into a single coherent bubble
                if (last.role === role) {
                  const updated = [...prev];
                  if (text.startsWith(last.text)) {
                    updated[updated.length - 1] = { ...last, text };
                  } else if (last.text.includes(text)) {
                    return prev;
                  } else {
                    updated[updated.length - 1] = {
                      ...last,
                      text: `${last.text} ${text}`,
                    };
                  }
                  return updated;
                }
                // Different speaker: create new turn
                return [...prev, { role, text, timestamp: time, isVoice: true }];
              });
              setTranscripts((prev) => {
                if (prev.length > 0 && prev[prev.length - 1].text === text) {
                  return prev;
                }
                return [...prev, { role, text }];
              });
            }
          }
        }
      });

      vapi.on("call-end", () => {
        setIsCalling(false);
        setAssistantVolume(0);
        setUserMicLevel(0);
        setLiveVapiTranscript("");
        setVoiceStatus("Call Ended");
      });

      vapi.on("error", (err) => {
        console.error("Vapi call error:", err);
        const errText = err?.error?.message || err?.message || (typeof err === "string" ? err : "Voice connection error");
        setVoiceStatus(`Call notice: ${errText}`);
      });

      await vapi.start(assistantId);
    } catch (err) {
      console.error("Voice connection error:", err);
      setIsCalling(false);
      setAssistantVolume(0);
      setUserMicLevel(0);
      setLiveVapiTranscript("");
      setVoiceStatus(`Failed: ${err.message || "Microphone access error"}`);
      setMicWarning(err.message || "Microphone initialization failed.");
    }
  };

  const stopVapiCall = () => {
    if (vapiRef.current) {
      try {
        vapiRef.current.stop();
      } catch (e) { }
    }
    setIsCalling(false);
    setAssistantVolume(0);
    setUserMicLevel(0);
    setLiveVapiTranscript("");
    setVoiceStatus("Ready to connect");
  };

  // =========================================================================
  // 2. BROWSER DIRECT VOICE MODE (Instant Web Speech STT + TTS)
  // =========================================================================
  const toggleBrowserVoice = () => {
    if (isBrowserListening) {
      stopBrowserVoice();
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser does not support the Web Speech API. Please use Google Chrome or Microsoft Edge.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = browserLang;
      recognition.interimResults = true;
      recognition.continuous = true;
      speechRecognitionRef.current = recognition;

      let currentTranscript = "";

      const dispatchVoiceTurn = (textToSend) => {
        const text = (textToSend || "").trim();
        if (!text || text.length < 2) return;
        currentTranscript = "";
        setBrowserSpeechText("");
        setVoiceStatus("Agent analyzing your request with LangGraph...");

        handleSendMessage(text).then((reply) => {
          if (reply) {
            setVoiceStatus("Agent speaking reply...");

            if (window.speechSynthesis) {
              window.speechSynthesis.cancel();
              const utterance = new SpeechSynthesisUtterance(reply.replace(/[\*#_]/g, ""));
              utterance.lang = browserLang;
              utterance.rate = 1.0;
              utterance.onend = () => {
                setVoiceStatus(`Listening... (${browserLang === "en-US" ? "English / UrduLish" : "Urdu"})`);
              };
              utterance.onerror = () => {
                setVoiceStatus("Ready to connect");
              };
              window.speechSynthesis.speak(utterance);
            }
          }
        });
      };

      recognition.onstart = () => {
        setIsBrowserListening(true);
        setVoiceStatus(`Listening... Speak now (${browserLang === "en-US" ? "English / UrduLish" : "Urdu"})`);
        setBrowserSpeechText("");
        setMicWarning("");
      };

      recognition.onresult = (event) => {
        let interim = "";
        let final = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            final += transcript;
          } else {
            interim += transcript;
          }
        }

        const combined = (final || interim).trim();
        if (combined) {
          currentTranscript = combined;
          setBrowserSpeechText(combined);

          clearTimeout(speechTimeoutRef.current);
          if (final && final.trim().length > 2) {
            dispatchVoiceTurn(final);
          } else {
            speechTimeoutRef.current = setTimeout(() => {
              if (currentTranscript && currentTranscript.length > 2) {
                dispatchVoiceTurn(currentTranscript);
              }
            }, 1500);
          }
        }
      };

      recognition.onerror = (event) => {
        console.warn("Speech recognition notice:", event.error);
        if (event.error === "not-allowed") {
          setMicWarning("Microphone access denied. Please allow microphone access in your browser.");
        }
      };

      recognition.onend = () => {
        setIsBrowserListening(false);
      };

      recognition.start();
    } catch (err) {
      console.error(err);
      setMicWarning("Failed to start browser microphone: " + err.message);
    }
  };

  const stopBrowserVoice = () => {
    clearTimeout(speechTimeoutRef.current);
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch (e) { }
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setIsBrowserListening(false);
    setBrowserSpeechText("");
    setVoiceStatus("Ready to connect");
  };

  if (!isOpen) return null;

  return (
    <div
      className={`fixed z-50 transition-all duration-300 ${isExpanded
        ? "inset-3 sm:inset-8"
        : "bottom-4 right-4 sm:bottom-6 sm:right-6 w-[94vw] sm:w-[460px] h-[670px] max-h-[92vh]"
        }`}
    >
      {/* Luxury Obsidian Glass Window */}
      <div className="w-full h-full bg-[#080d1a] border border-amber-400/30 rounded-3xl shadow-[0_25px_80px_rgba(0,0,0,0.95),0_0_40px_rgba(245,180,100,0.18)] flex flex-col overflow-hidden relative select-none">
        {/* Specular Top Gold Rim Highlight */}
        <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-amber-400/50 to-transparent pointer-events-none z-20" />

        {/* Ambient Warm Villa Glow Leaks */}
        <div className="absolute -top-24 -right-24 w-60 h-60 rounded-full bg-amber-500/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-60 h-60 rounded-full bg-amber-500/5 blur-3xl pointer-events-none" />

        {/* ================= HEADER ================= */}
        <div className="px-4 sm:px-5 py-3.5 bg-[#0b101c] border-b border-amber-400/20 flex items-center justify-between z-10">
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-amber-500 to-amber-300 p-[1.5px] shadow-sm">
                <div className="w-full h-full bg-[#090d18] rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-amber-300" />
                </div>
              </div>
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-[#090d18] absolute -top-0.5 -right-0.5 shadow-[0_0_8px_rgba(52,211,153,0.9)] animate-pulse" />
            </div>
            <div>
              <h3 className="font-display-serif font-normal text-sm sm:text-base text-white flex items-center gap-2">
                <span>AI Property Consultant</span>
                <span className="text-[10px] font-sans font-medium px-2 py-0.5 rounded-full bg-amber-400/10 text-amber-300 border border-amber-400/25">
                  LangGraph
                </span>
              </h3>
              <p className="text-[10px] text-amber-200/60 font-light">Urdu & English Voice Consultant</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Mode Switcher (Chat vs Voice) */}
            <div className="flex bg-[#060912] p-1 rounded-xl border border-white/10 mr-1">
              <button
                onClick={() => {
                  stopVapiCall();
                  stopBrowserVoice();
                  setActiveMode("chat");
                }}
                className={`px-3 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${activeMode === "chat"
                  ? "bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20"
                  : "text-slate-400 hover:text-white"
                  }`}
              >
                <MessageSquare className="w-3 h-3" />
                <span>Chat</span>
              </button>
              <button
                onClick={() => setActiveMode("voice")}
                className={`px-3 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${activeMode === "voice"
                  ? "bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20"
                  : "text-slate-400 hover:text-white"
                  }`}
              >
                <Mic className="w-3 h-3" />
                <span>Voice</span>
              </button>
            </div>

            {/* Expand / Minimize */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              aria-label="Expand view"
              className="p-1.5 rounded-lg text-slate-400 hover:text-amber-300 hover:bg-white/5 transition-colors cursor-pointer"
            >
              {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>

            {/* Close */}
            <button
              onClick={() => {
                stopVapiCall();
                stopBrowserVoice();
                onClose();
              }}
              aria-label="Close assistant"
              className="p-1.5 rounded-lg text-slate-400 hover:text-amber-300 hover:bg-white/5 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ================= BODY CONTENT ================= */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden z-10">

          {/* VOICE MODE STUDIO BAR (Shown in Voice Mode at Top) */}
          {activeMode === "voice" && (
            <div className="p-3.5 sm:p-4 bg-[#0c1222]/95 border-b border-amber-400/20 flex flex-col gap-2.5 flex-shrink-0">
              {/* Sub-mode Switcher */}
              <div className="flex items-center justify-between gap-2 p-1 rounded-xl bg-[#060a14] border border-white/10">
                <button
                  onClick={() => {
                    stopBrowserVoice();
                    setVoiceSubMode("vapi");
                  }}
                  className={`flex-1 py-1.5 px-2 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${voiceSubMode === "vapi"
                    ? "bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 font-bold shadow-sm"
                    : "text-slate-400 hover:text-white"
                    }`}
                >
                  <Radio className="w-3 h-3" />
                  Vapi Cloud Call (Urdu Nova-3)
                </button>
                <button
                  onClick={() => {
                    stopVapiCall();
                    setVoiceSubMode("browser");
                  }}
                  className={`flex-1 py-1.5 px-2 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${voiceSubMode === "browser"
                    ? "bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 font-bold shadow-sm"
                    : "text-slate-400 hover:text-white"
                    }`}
                >
                  <Mic className="w-3 h-3" />
                  Direct Browser Mic
                </button>
              </div>

              {/* Live Voice Visualizer & Main Action Row */}
              <div className="flex items-center justify-between gap-3 bg-[#080d18] p-3 rounded-2xl border border-amber-400/25">
                {/* Visualizer Orb */}
                <div className="relative flex items-center justify-center flex-shrink-0">
                  <div
                    className={`w-12 h-12 rounded-full bg-gradient-to-tr from-amber-500/20 via-amber-400/30 to-amber-500/20 flex items-center justify-center ${(isCalling || isBrowserListening) ? "animate-pulse" : ""
                      }`}
                    style={{
                      transform: `scale(${1 + Math.max(assistantVolume, userMicLevel) * 0.35})`,
                      transition: "transform 0.1s ease-out",
                    }}
                  >
                    <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-amber-400 to-amber-500 p-[1.5px] shadow-lg shadow-amber-500/30">
                      <div className="w-full h-full bg-[#080d18] rounded-full flex items-center justify-center">
                        {assistantVolume > 0.08 ? (
                          <Volume2 className="w-4 h-4 text-amber-300 animate-bounce" />
                        ) : userMicLevel > 0.05 ? (
                          <Mic className="w-4 h-4 text-emerald-400 animate-pulse" />
                        ) : (
                          <Mic className="w-4 h-4 text-amber-300" />
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Status & Sub-badge */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={`w-2 h-2 rounded-full ${isCalling || isBrowserListening ? "bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.9)]" : "bg-amber-400/60"}`} />
                    <span className="text-[10px] uppercase font-bold tracking-wider text-amber-300 truncate">
                      {voiceSubMode === "vapi" ? "Autonomous Voice Agent" : "Direct Speech RAG"}
                    </span>
                  </div>
                  <p className="text-xs text-white font-medium truncate">
                    {voiceStatus}
                  </p>
                </div>

                {/* Call Primary Button */}
                <div className="flex-shrink-0">
                  {voiceSubMode === "vapi" ? (
                    !isCalling ? (
                      <button
                        onClick={startVapiCall}
                        className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-amber-500/25 transition-all cursor-pointer"
                      >
                        <PhoneCall className="w-3.5 h-3.5" />
                        <span>Start Call</span>
                      </button>
                    ) : (
                      <button
                        onClick={stopVapiCall}
                        className="px-3.5 py-2 rounded-xl bg-red-500 hover:bg-red-400 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-red-500/30 transition-all animate-pulse cursor-pointer"
                      >
                        <PhoneOff className="w-3.5 h-3.5" />
                        <span>End Call</span>
                      </button>
                    )
                  ) : (
                    !isBrowserListening ? (
                      <button
                        onClick={toggleBrowserVoice}
                        className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-amber-500/25 transition-all cursor-pointer"
                      >
                        <Mic className="w-3.5 h-3.5" />
                        <span>Start Talk</span>
                      </button>
                    ) : (
                      <button
                        onClick={stopBrowserVoice}
                        className="px-3.5 py-2 rounded-xl bg-red-500 hover:bg-red-400 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-red-500/30 transition-all animate-pulse cursor-pointer"
                      >
                        <MicOff className="w-3.5 h-3.5" />
                        <span>Stop Mic</span>
                      </button>
                    )
                  )}
                </div>
              </div>

              {/* Audio Settings Dropdown Toggle */}
              <div className="flex items-center justify-between text-[10px] text-slate-400 px-1">
                <span className="flex items-center gap-1">
                  <span>Mic Level:</span>
                  <span className={userMicLevel > 0.03 ? "text-emerald-400 font-mono font-bold" : "text-slate-500 font-mono"}>
                    {Math.round(userMicLevel * 100)}%
                  </span>
                </span>

                <button
                  onClick={() => setShowAudioSettings(!showAudioSettings)}
                  className="flex items-center gap-1 text-amber-300/80 hover:text-amber-200 transition-colors cursor-pointer"
                >
                  <Settings2 className="w-3 h-3" />
                  <span>{showAudioSettings ? "Hide Settings" : "Audio Settings"}</span>
                  {showAudioSettings ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
              </div>

              {/* Collapsible Audio Hardware Settings */}
              {showAudioSettings && (
                <div className="p-3 rounded-xl bg-[#080d18] border border-white/10 space-y-2 text-[10px]">
                  {audioDevices.length > 0 && (
                    <div>
                      <div className="flex items-center justify-between text-slate-400 mb-1">
                        <span>Input Device:</span>
                        <button
                          onClick={refreshAudioDevices}
                          className="text-amber-300 hover:text-amber-200 flex items-center gap-0.5 cursor-pointer"
                        >
                          <RefreshCw className="w-2.5 h-2.5" />
                          <span>refresh</span>
                        </button>
                      </div>
                      <select
                        value={selectedDeviceId}
                        onChange={(e) => {
                          setSelectedDeviceId(e.target.value);
                          if (isTestingMic) {
                            stopMicTestStream();
                            setIsTestingMic(false);
                          }
                        }}
                        className="w-full bg-[#060a14] border border-white/15 rounded-lg text-[10px] text-slate-200 px-2 py-1 outline-none focus:border-amber-400 truncate"
                      >
                        {audioDevices.map((dev, idx) => (
                          <option key={dev.deviceId || idx} value={dev.deviceId}>
                            {dev.label || `Microphone Device ${idx + 1}`}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-1">
                    <button
                      onClick={testMicrophoneInput}
                      className={`flex items-center gap-1 font-semibold transition-colors cursor-pointer ${isTestingMic ? "text-amber-400 hover:text-amber-300 animate-pulse" : "text-amber-300/80 hover:text-amber-200"
                        }`}
                    >
                      <RefreshCw className={`w-3 h-3 ${isTestingMic ? "animate-spin" : ""}`} />
                      <span>{isTestingMic ? "Stop Mic Test" : "Test Hardware Microphone"}</span>
                    </button>

                    {voiceSubMode === "browser" && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-400">Language:</span>
                        <button
                          onClick={() => setBrowserLang("en-US")}
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold border transition-all ${browserLang === "en-US"
                            ? "bg-amber-400/20 text-amber-300 border-amber-400/40"
                            : "bg-[#060a14] text-slate-400 border-white/10"
                            }`}
                        >
                          UrduLish
                        </button>
                        <button
                          onClick={() => setBrowserLang("ur-PK")}
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold border transition-all ${browserLang === "ur-PK"
                            ? "bg-amber-400/20 text-amber-300 border-amber-400/40"
                            : "bg-[#060a14] text-slate-400 border-white/10"
                            }`}
                        >
                          اردو
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Warning Alert */}
              {micWarning && (
                <div className="p-2 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[10px] flex items-center gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 text-amber-400" />
                  <span>{micWarning}</span>
                </div>
              )}
            </div>
          )}

          {/* ================= FULL CHAT STREAM (SHOWN IN BOTH CHAT & VOICE) ================= */}
          <div
            ref={chatScrollRef}
            className="flex-1 p-4 overflow-y-auto space-y-3.5 select-text"
          >
            {(activeMode === "voice" ? voiceMessages : messages).map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "assistant" && (
                  <div className="w-6 h-6 rounded-full bg-amber-400/10 border border-amber-400/30 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                    <Bot className="w-3.5 h-3.5 text-amber-300" />
                  </div>
                )}

                <div className={`max-w-[84%] space-y-2 ${m.role === "user" ? "items-end" : "items-start"}`}>
                  <div
                    className={`p-3.5 rounded-2xl text-xs leading-relaxed ${m.role === "user"
                      ? "bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 font-semibold rounded-tr-none shadow-md shadow-amber-500/15"
                      : "bg-[#0e1526] border border-amber-400/15 text-slate-200 rounded-tl-none shadow-sm"
                      }`}
                  >
                    <p className="whitespace-pre-wrap">{m.text}</p>
                  </div>

                  {/* Inline Property Recommendation Cards */}
                  {m.properties && m.properties.length > 0 && (
                    <div className="space-y-2 mt-2">
                      <div className="text-[10px] font-semibold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                        <Sparkles className="w-3 h-3 text-amber-400" />
                        <span>Recommended Matches:</span>
                      </div>
                      <div className="grid grid-cols-1 gap-2">
                        {m.properties.map((p, pIdx) => (
                          <div
                            key={pIdx}
                            className="p-3 rounded-xl bg-[#060a14] border border-amber-400/30 hover:border-amber-400/60 transition-all flex items-center justify-between gap-3 shadow-md"
                          >
                            <div className="min-w-0">
                              <div className="text-xs font-bold text-white truncate">
                                {p.area_marla} Marla in {p.locality}
                              </div>
                              <div className="text-xs text-amber-300 font-bold font-mono mt-0.5">
                                {formatPKR(p.price)}
                              </div>
                            </div>
                            <button
                              onClick={() => onBookVisit && onBookVisit(p)}
                              className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 text-[10px] font-bold shadow-sm transition-all flex-shrink-0 cursor-pointer"
                            >
                              Book Visit
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-1.5 text-[9px] text-slate-500 px-1">
                    <span>{m.timestamp}</span>
                    {m.isVoice && (
                      <Mic className="w-2.5 h-2.5 text-amber-400/70" />
                    )}
                  </div>
                </div>

                {m.role === "user" && (
                  <div className="w-6 h-6 rounded-full bg-white/10 border border-white/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <User className="w-3.5 h-3.5 text-slate-300" />
                  </div>
                )}
              </div>
            ))}

            {/* Live Spoken Speech Preview (while user is currently talking) */}
            {(browserSpeechText || liveVapiTranscript) && (
              <div className="flex gap-2.5 justify-end animate-pulse">
                <div className="max-w-[82%] p-3 rounded-2xl rounded-tr-none bg-amber-400/15 border border-amber-400/40 text-amber-200 text-xs flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping flex-shrink-0" />
                  <span>"{browserSpeechText || liveVapiTranscript}"</span>
                </div>
                <div className="w-6 h-6 rounded-full bg-amber-400/20 border border-amber-400/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Mic className="w-3 h-3 text-amber-300" />
                </div>
              </div>
            )}

            {/* Thinking / Searching Indicator */}
            {sending && (
              <div className="flex items-center gap-2 text-xs text-amber-300 bg-[#0c1322] p-3 rounded-xl border border-amber-400/20 w-fit">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                <span>Agent analyzing verified database...</span>
              </div>
            )}
          </div>

          {/* Quick Prompt Chips */}
          <div className="px-4 py-2 bg-[#060a14]/90 border-t border-white/10 flex gap-1.5 overflow-x-auto">
            <button
              onClick={() => handleSendMessage("5 Marla in DHA Lahore under 2 Crore")}
              className="px-3 py-1 rounded-full bg-white/5 hover:bg-amber-400/15 border border-white/10 hover:border-amber-400/40 text-slate-300 hover:text-amber-200 text-[10px] font-medium whitespace-nowrap transition-all cursor-pointer"
            >
              🏡 5 Marla DHA under 2 Cr
            </button>
            <button
              onClick={() => handleSendMessage("I want to schedule a visit tomorrow at 3 PM")}
              className="px-3 py-1 rounded-full bg-white/5 hover:bg-amber-400/15 border border-white/10 hover:border-amber-400/40 text-slate-300 hover:text-amber-200 text-[10px] font-medium whitespace-nowrap transition-all cursor-pointer"
            >
              📅 Schedule visit tomorrow
            </button>
            <button
              onClick={() => handleSendMessage("Bahria Town facilities aur payment plan")}
              className="px-3 py-1 rounded-full bg-white/5 hover:bg-amber-400/15 border border-white/10 hover:border-amber-400/40 text-slate-300 hover:text-amber-200 text-[10px] font-medium whitespace-nowrap transition-all cursor-pointer"
            >
              🌟 Bahria Town info
            </button>
          </div>

          {/* Input Bar */}
          <div className="p-3 bg-[#0b101c] border-t border-amber-400/20 flex items-center gap-2">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Ask in Urdu or English..."
              className="flex-1 px-4 py-2.5 rounded-xl bg-[#060a14] border border-white/15 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400/30 transition-all"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputText.trim() || sending}
              className="p-2.5 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-bold text-xs disabled:opacity-40 transition-all cursor-pointer shadow-md shadow-amber-500/20"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

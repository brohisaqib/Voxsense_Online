/**
 * VoxSense — app.js
 * WebSocket client + Web Speech API controller
 * Designed for blind users — full keyboard + voice only
 */

'use strict';

/* ═══════════════════════════════════════════════
   CONFIG
   ═══════════════════════════════════════════════ */
const CONFIG = {
  WS_URL:          'ws://localhost:8000/ws',
  HTTP_URL:        'http://localhost:8000',
  RECONNECT_DELAY: 3000,
  MAX_RECONNECTS:  10,
  SPEECH_LANG:     'en-US',
  SPEECH_RATE:     0.9,
  SPEECH_PITCH:    1.0,
  SPEECH_VOLUME:   1.0,
};

/* ═══════════════════════════════════════════════
   STATE
   ═══════════════════════════════════════════════ */
const state = {
  ws:                null,
  isListening:       false,
  isSpeaking:        false,
  isThinking:        false,
  reconnectAttempts: 0,
  awaitingConfirm:   false,
  pendingAction:     null,
  confirmCallbacks:  { yes: null, no: null },
};

/* ═══════════════════════════════════════════════
   DOM REFERENCES
   ═══════════════════════════════════════════════ */
const el = {
  micBtn:        document.getElementById('micBtn'),
  statusAnnounce:document.getElementById('status-announce'),
  connBadge:     document.getElementById('connection-status'),
  nvdaBadge:     document.getElementById('nvda-status'),
  userSaid:      document.getElementById('userSaid'),
  aiResponse:    document.getElementById('aiResponse'),
  convTrack:     document.getElementById('conversationTrack'),
  confirmOverlay:document.getElementById('confirmOverlay'),
  confirmHeading:document.getElementById('confirm-heading'),
  confirmDesc:   document.getElementById('confirm-desc'),
  confirmYes:    document.getElementById('confirmYes'),
  confirmNo:     document.getElementById('confirmNo'),
  year:          document.getElementById('year'),
};

/* ═══════════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  el.year.textContent = new Date().getFullYear();
  el.userSaid.setAttribute('data-placeholder', 'Waiting for your voice…');
  el.aiResponse.setAttribute('data-placeholder', 'Assistant response will appear here…');
  initWebSocket();
  initSpeechRecognition();
  initEventListeners();
  checkStatus();
  announceToScreenReader('VoxSense is ready. Press Space to speak.');
});

/* ═══════════════════════════════════════════════
   WEBSOCKET
   ═══════════════════════════════════════════════ */
function initWebSocket() {
  setStatus('Connecting…', 'thinking');

  try {
    state.ws = new WebSocket(CONFIG.WS_URL);
  } catch (err) {
    handleConnectionError();
    return;
  }

  state.ws.onopen = () => {
    state.reconnectAttempts = 0;
    setBadge(el.connBadge, 'connected', '● Connected');
    el.connBadge.setAttribute('aria-label', 'Connection status: connected');
    setStatus('Ready — Press Space to speak', 'ready');
    announceToScreenReader('Connected to VoxSense backend. Ready to listen.');
  };

  state.ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleServerMessage(data);
    } catch (e) {
      console.error('WS parse error:', e);
    }
  };

  state.ws.onerror = () => {
    handleConnectionError();
  };

  state.ws.onclose = () => {
    setBadge(el.connBadge, 'disconnected', '○ Disconnected');
    el.connBadge.setAttribute('aria-label', 'Connection status: disconnected');
    scheduleReconnect();
  };
}

function scheduleReconnect() {
  if (state.reconnectAttempts >= CONFIG.MAX_RECONNECTS) {
    setStatus('Backend not reachable. Is the server running?', 'error');
    announceToScreenReader('Cannot connect to backend. Please ensure the VoxSense server is running on port 8000.');
    return;
  }
  state.reconnectAttempts++;
  const delay = CONFIG.RECONNECT_DELAY * state.reconnectAttempts;
  setStatus(`Reconnecting… (attempt ${state.reconnectAttempts})`, 'thinking');
  setTimeout(initWebSocket, delay);
}

function handleConnectionError() {
  setBadge(el.connBadge, 'disconnected', '○ Disconnected');
  setStatus('Cannot connect to backend. Make sure start.bat was run.', 'error');
}

function sendToBackend(transcript) {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
    speakText('Not connected to the backend. Please wait while I reconnect.');
    setStatus('Not connected — retrying…', 'error');
    initWebSocket();
    return;
  }
  state.ws.send(JSON.stringify({ transcript: transcript.trim() }));
}

/* ═══════════════════════════════════════════════
   SERVER MESSAGE HANDLER
   ═══════════════════════════════════════════════ */
function handleServerMessage(data) {
  // Confirmation request from backend
  if (data.type === 'confirm_request') {
    showConfirmDialog(
      data.message,
      () => sendToBackend('yes confirm'),
      () => sendToBackend('cancel')
    );
    speakText(data.message);
    return;
  }

  // Error
  if (data.type === 'error') {
    const msg = data.response || 'Sorry, something went wrong. Please try again.';
    displayAIResponse(msg);
    speakText(msg);
    setStatus('Error — Ready to listen again', 'error');
    return;
  }

  // Normal response
  const response = data.response || 'Done.';
  const intent   = data.intent   || '';

  displayAIResponse(response);
  speakText(response);
  setStatus('Done — Press Space to speak again', 'ready');

  // Append to conversation log
  appendMessage('ai', response);
}

/* ═══════════════════════════════════════════════
   SPEECH RECOGNITION (Web Speech API)
   ═══════════════════════════════════════════════ */
let recognition = null;

function initSpeechRecognition() {
  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    setStatus('Speech recognition not supported. Please use Chrome or Edge.', 'error');
    announceToScreenReader('Your browser does not support speech recognition. Please open this page in Google Chrome or Microsoft Edge.');
    el.micBtn.disabled = true;
    el.micBtn.setAttribute('aria-label', 'Speech recognition not available in this browser');
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous  = false;
  recognition.interimResults = true;
  recognition.lang        = CONFIG.SPEECH_LANG;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    state.isListening = true;
    el.micBtn.setAttribute('aria-pressed', 'true');
    el.micBtn.querySelector('.mic-state-label').textContent = 'Listening…';
    setStatus('Listening… Speak now', 'listening');
  };

  recognition.onresult = (event) => {
    let interim = '';
    let final   = '';

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        final += transcript;
      } else {
        interim += transcript;
      }
    }

    // Show interim transcript
    if (interim) {
      el.userSaid.textContent = interim;
    }

    // Final — send to backend
    if (final) {
      const text = final.trim();
      el.userSaid.textContent = text;
      appendMessage('user', text);
      setStatus('Processing…', 'thinking');
      sendToBackend(text);
    }
  };

  recognition.onspeechend = () => {
    recognition.stop();
  };

  recognition.onend = () => {
    state.isListening = false;
    el.micBtn.setAttribute('aria-pressed', 'false');
    el.micBtn.querySelector('.mic-state-label').textContent = 'Hold to Talk';
  };

  recognition.onerror = (event) => {
    state.isListening = false;
    el.micBtn.setAttribute('aria-pressed', 'false');
    el.micBtn.querySelector('.mic-state-label').textContent = 'Hold to Talk';

    const errorMessages = {
      'not-allowed':      'Microphone permission denied. Please allow microphone access and refresh.',
      'no-speech':        'No speech detected. Please try again.',
      'audio-capture':    'Microphone not found. Please check your microphone.',
      'network':          'Network error during speech recognition.',
      'aborted':          'Listening cancelled.',
      'service-not-allowed': 'Speech service not allowed.',
    };

    const msg = errorMessages[event.error] || `Speech error: ${event.error}. Please try again.`;

    if (event.error !== 'aborted' && event.error !== 'no-speech') {
      setStatus(msg, 'error');
      speakText(msg);
    } else {
      setStatus('Ready — Press Space to speak', 'ready');
    }
  };
}

function startListening() {
  if (!recognition) return;
  if (state.isSpeaking) {
    window.speechSynthesis.cancel();
    state.isSpeaking = false;
  }
  if (state.isListening) return;

  try {
    recognition.start();
  } catch (e) {
    console.warn('Recognition already started:', e);
  }
}

function stopListening() {
  if (!recognition || !state.isListening) return;
  try {
    recognition.stop();
  } catch (e) {
    console.warn('Recognition stop error:', e);
  }
}

function toggleListening() {
  if (state.isListening) {
    stopListening();
  } else {
    startListening();
  }
}

/* ═══════════════════════════════════════════════
   SPEECH SYNTHESIS
   ═══════════════════════════════════════════════ */
const synth = window.speechSynthesis;

function speakText(text, priority = false) {
  if (!text || !synth) return;

  // Cancel current speech if priority (user pressed mic again)
  if (priority) synth.cancel();

  const utt = new SpeechSynthesisUtterance(text);
  utt.lang   = CONFIG.SPEECH_LANG;
  utt.rate   = CONFIG.SPEECH_RATE;
  utt.pitch  = CONFIG.SPEECH_PITCH;
  utt.volume = CONFIG.SPEECH_VOLUME;

  utt.onstart = () => {
    state.isSpeaking = true;
    setStatus('Speaking…', 'speaking');
  };

  utt.onend = () => {
    state.isSpeaking = false;
    // Don't change status if we're in a different state
    if (!state.isListening && !state.isThinking) {
      setStatus('Ready — Press Space to speak', 'ready');
    }
  };

  utt.onerror = (e) => {
    if (e.error !== 'interrupted') {
      console.warn('Speech synthesis error:', e.error);
    }
    state.isSpeaking = false;
  };

  synth.speak(utt);
}

/* ═══════════════════════════════════════════════
   UI HELPERS
   ═══════════════════════════════════════════════ */
function setStatus(text, type = 'ready') {
  el.statusAnnounce.textContent = text;
  el.statusAnnounce.className = 'status-announce';

  const typeMap = {
    listening: 'status--listening',
    thinking:  'status--thinking',
    speaking:  'status--speaking',
    error:     'status--error',
    ready:     '',
  };

  if (typeMap[type]) {
    el.statusAnnounce.classList.add(typeMap[type]);
  }
}

function displayAIResponse(text) {
  el.aiResponse.textContent = text;
  // Scroll conversation into view
  el.convTrack.scrollTop = el.convTrack.scrollHeight;
}

function appendMessage(role, text) {
  const div  = document.createElement('div');
  div.className = `message message--${role}`;
  div.setAttribute('role', 'listitem');

  const icon = document.createElement('span');
  icon.className = 'message-icon';
  icon.setAttribute('aria-hidden', 'true');
  icon.textContent = role === 'user' ? '▶' : '◈';

  const p = document.createElement('p');
  p.textContent = text;

  div.appendChild(icon);
  div.appendChild(p);

  el.convTrack.appendChild(div);
  el.convTrack.scrollTop = el.convTrack.scrollHeight;
}

function setBadge(badgeEl, type, text) {
  badgeEl.className = `badge badge--${type}`;
  badgeEl.querySelector('.badge-text').textContent = text.replace('● ', '').replace('○ ', '');
}

function announceToScreenReader(text) {
  // Create a temporary live region for one-time announcements
  const tmp = document.createElement('div');
  tmp.setAttribute('aria-live', 'assertive');
  tmp.setAttribute('role', 'alert');
  tmp.style.position   = 'absolute';
  tmp.style.width      = '1px';
  tmp.style.height     = '1px';
  tmp.style.overflow   = 'hidden';
  tmp.style.clipPath   = 'inset(50%)';
  document.body.appendChild(tmp);
  // Small delay so screen reader picks up the insertion
  setTimeout(() => {
    tmp.textContent = text;
    setTimeout(() => document.body.removeChild(tmp), 3000);
  }, 100);
}

/* ═══════════════════════════════════════════════
   CONFIRMATION DIALOG
   ═══════════════════════════════════════════════ */
function showConfirmDialog(message, onYes, onNo) {
  state.awaitingConfirm = true;
  state.confirmCallbacks.yes = onYes;
  state.confirmCallbacks.no  = onNo;

  el.confirmDesc.textContent = message;
  el.confirmOverlay.hidden   = false;
  el.confirmOverlay.removeAttribute('hidden');

  // Focus the yes button
  requestAnimationFrame(() => el.confirmYes.focus());
}

function closeConfirmDialog() {
  state.awaitingConfirm = false;
  state.confirmCallbacks.yes = null;
  state.confirmCallbacks.no  = null;
  el.confirmOverlay.hidden = true;
  el.confirmOverlay.setAttribute('hidden', '');
  el.micBtn.focus();
}

el.confirmYes.addEventListener('click', () => {
  closeConfirmDialog();
  if (state.confirmCallbacks.yes) state.confirmCallbacks.yes();
});

el.confirmNo.addEventListener('click', () => {
  closeConfirmDialog();
  if (state.confirmCallbacks.no) state.confirmCallbacks.no();
  speakText('Action cancelled.');
  setStatus('Cancelled — Ready to listen', 'ready');
});

/* ═══════════════════════════════════════════════
   BACKEND STATUS CHECK
   ═══════════════════════════════════════════════ */
async function checkStatus() {
  try {
    const res  = await fetch(`${CONFIG.HTTP_URL}/status`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();

    if (data.nvda_connected) {
      setBadge(el.nvdaBadge, 'nvda-on', 'NVDA On');
      el.nvdaBadge.setAttribute('aria-label', 'NVDA screen reader: active');
    } else {
      setBadge(el.nvdaBadge, 'off', 'NVDA Off');
      el.nvdaBadge.setAttribute('aria-label', 'NVDA screen reader: not detected');
    }
  } catch (_) {
    // Backend not yet reachable — WS reconnect will handle this
  }
}

/* ═══════════════════════════════════════════════
   EVENT LISTENERS
   ═══════════════════════════════════════════════ */
function initEventListeners() {
  // MIC BUTTON — click
  el.micBtn.addEventListener('click', () => {
    if (state.isSpeaking) {
      synth.cancel();
      state.isSpeaking = false;
    }
    toggleListening();
  });

  // SPACE BAR — primary trigger (anywhere on page)
  document.addEventListener('keydown', (e) => {
    // Ignore when typing in an input
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;

    if (e.code === 'Space' && !e.repeat) {
      e.preventDefault();

      // If confirmation dialog is open
      if (state.awaitingConfirm) {
        el.confirmYes.click();
        return;
      }

      if (state.isSpeaking) {
        synth.cancel();
        state.isSpeaking = false;
      }
      toggleListening();
    }

    // ESC — cancel listening or speaking
    if (e.key === 'Escape') {
      if (state.awaitingConfirm) {
        el.confirmNo.click();
        return;
      }
      if (state.isListening) {
        stopListening();
        setStatus('Cancelled — Press Space to speak', 'ready');
      }
      if (state.isSpeaking) {
        synth.cancel();
        state.isSpeaking = false;
        setStatus('Ready — Press Space to speak', 'ready');
      }
    }

    // Y key — confirm dialog shortcut
    if ((e.key === 'y' || e.key === 'Y') && state.awaitingConfirm) {
      el.confirmYes.click();
    }

    // N key — cancel dialog shortcut
    if ((e.key === 'n' || e.key === 'N') && state.awaitingConfirm) {
      el.confirmNo.click();
    }
  });

  // CMD CHIPS — clicking one starts listening (as a hint)
  document.querySelectorAll('.cmd-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      startListening();
    });

    chip.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.code === 'Space') {
        e.preventDefault();
        startListening();
      }
    });
  });

  // Periodically re-check NVDA/backend status
  setInterval(checkStatus, 30000);

  // Handle page visibility — resume if needed
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && state.ws?.readyState !== WebSocket.OPEN) {
      initWebSocket();
    }
  });
}

/* ═══════════════════════════════════════════════
   KEYBOARD SHORTCUT GUIDE (F1 — reads shortcuts)
   ═══════════════════════════════════════════════ */
document.addEventListener('keydown', (e) => {
  if (e.key === 'F1') {
    e.preventDefault();
    const guide = [
      'Keyboard shortcuts.',
      'Space bar: Start or stop listening.',
      'Escape: Cancel listening or speaking.',
      'Tab: Navigate between elements.',
      'Enter or Space on a Quick Command chip: Start listening.',
      'Y key: Confirm a pending action.',
      'N key: Cancel a pending action.',
      'F1: Read this keyboard guide.',
    ].join(' ');
    speakText(guide, true);
    announceToScreenReader(guide);
  }
});
/**
 * FieldWise AI (نبتة) - Farmer Voice Assistant Client Application
 */

const API_BASE = window.location.origin;

// State management
let currentSessionId = null;
let currentRecommendations = null;
let isRecording = false;
let recognition = null;

// DOM Elements
const micBtn = document.getElementById('micBtn');
const micStatus = document.getElementById('micStatus');
const micHint = document.getElementById('micHint');
const liveTranscriptBox = document.getElementById('liveTranscriptBox');
const confirmationCard = document.getElementById('confirmationCard');
const confirmationText = document.getElementById('confirmationText');
const btnConfirmYes = document.getElementById('btnConfirmYes');
const btnConfirmNo = document.getElementById('btnConfirmNo');
const recommendationsContainer = document.getElementById('recommendationsContainer');
const plansList = document.getElementById('plansList');
const tapFallbackForm = document.getElementById('tapFallbackForm');

// Initialize Web Speech Recognition
function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micHint.innerText = 'المتصفح لا يدعم التسجيل المباشر، يمكنك استخدام الاختيارات بالأسفل.';
    return null;
  }

  const rec = new SpeechRecognition();
  rec.lang = 'ar-EG';
  rec.continuous = false;
  rec.interimResults = true;

  rec.onstart = () => {
    isRecording = true;
    micBtn.classList.add('listening');
    micStatus.innerText = 'سامعك يا حاج... اتكلم';
    micHint.innerText = 'قول مثلاً: عندي تلات فدادين في كفر الشيخ وبنروي بالمناوبة';
    liveTranscriptBox.style.display = 'block';
    liveTranscriptBox.innerText = '...';
  };

  rec.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript;
    }
    liveTranscriptBox.innerText = transcript;
  };

  rec.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    stopRecording();
    micStatus.innerText = 'دوس هنا واتكلم';
    micHint.innerText = 'حصل خطأ في التقاط الصوت، جرب تاني أو اختار من تحت.';
  };

  rec.onend = () => {
    if (isRecording) {
      stopRecording();
      const text = liveTranscriptBox.innerText.trim();
      if (text && text !== '...') {
        submitFarmerUtterance(text);
      } else {
        micStatus.innerText = 'دوس هنا واتكلم';
      }
    }
  };

  return rec;
}

function startRecording() {
  if (!recognition) recognition = initSpeechRecognition();
  if (recognition) {
    try {
      recognition.start();
    } catch (e) {
      console.warn('Recognition already started:', e);
    }
  }
}

function stopRecording() {
  isRecording = false;
  micBtn.classList.remove('listening');
  if (recognition) {
    try {
      recognition.stop();
    } catch (e) {}
  }
}

// Speak Arabic text using Web Speech Synthesis
function speakArabic(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel(); // Stop any ongoing speech

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'ar-EG';
  utterance.rate = 0.95; // Gentle pace for Egyptian farmers

  // Try to pick an Arabic voice if available
  const voices = window.speechSynthesis.getVoices();
  const arVoice = voices.find((v) => v.lang.startsWith('ar'));
  if (arVoice) utterance.voice = arVoice;

  window.speechSynthesis.speak(utterance);
}

// Submit voice transcript to FastAPI backend
async function submitFarmerUtterance(transcript) {
  micStatus.innerText = 'بنفهم كلامك...';
  try {
    const res = await fetch(`${API_BASE}/api/voice/process-utterance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ utterance: transcript, session_id: currentSessionId }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'تعذر معالجة الكلام');
    }

    const data = await res.json();
    currentSessionId = data.session_id;

    // Show confirmation card
    showConfirmationDialogue(data.spoken_prompt_ar);
  } catch (err) {
    console.error('API Error:', err);
    micStatus.innerText = 'دوس هنا واتكلم';
    alert('معلش يا حاج، الصوت مكنش واضح. جرب تاني أو اختار باللمس.');
  }
}

function showConfirmationDialogue(promptText) {
  micStatus.innerText = 'تأكيد البيانات';
  confirmationText.innerText = promptText;
  confirmationCard.style.display = 'flex';
  speakArabic(promptText);
}

// Confirm dialog response
async function handleConfirmation(isConfirmed) {
  if (!isConfirmed) {
    confirmationCard.style.display = 'none';
    micStatus.innerText = 'دوس هنا واتكلم';
    speakArabic('تمام يا حاج، قولي تاني اللي تحب تعدله.');
    return;
  }

  confirmationCard.style.display = 'none';
  micStatus.innerText = 'بنحسب أفضل محصول لأرضك...';

  try {
    const res = await fetch(`${API_BASE}/api/voice/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSessionId, farmer_reply: 'أيوه تمام' }),
    });

    const data = await res.json();
    if (data.status === 'CONFIRMED' && data.recommendation_response) {
      renderRecommendations(data.recommendation_response);
      if (data.spoken_recommendations_ar) {
        speakArabic(data.spoken_recommendations_ar);
      }
    }
  } catch (err) {
    console.error('Confirmation error:', err);
    alert('تعذر استخراج النتائج من المحرك. جرب تاني.');
  }
}

// Render the 3 recommendation plans
function renderRecommendations(recData) {
  currentRecommendations = recData;
  plansList.innerHTML = '';

  const plans = recData.recommendations;
  plans.forEach((plan) => {
    const archetypeClass = plan.archetype === 'الأكسب' ? 'profit' : plan.archetype === 'الأوفر في المية' ? 'water' : 'safety';
    const m = plan.metrics;

    const card = document.createElement('div');
    card.className = `plan-card ${archetypeClass}`;
    card.innerHTML = `
      <div class="plan-badge">${plan.archetype}</div>
      <div class="plan-crop-name">${plan.primary_crop_ar}</div>
      <div class="plan-metrics-row">
        <span>صافي الربح للفدان:</span>
        <span class="plan-metric-val">${Math.round(m.net_profit_egp_per_feddan).toLocaleString('ar-EG')} جنيه</span>
      </div>
      <div class="plan-metrics-row">
        <span>استهلاك المية للفدان:</span>
        <span class="plan-metric-val">${Math.round(m.water_demand_m3_per_feddan).toLocaleString('ar-EG')} م³</span>
      </div>
      <div class="plan-advice">💡 ${plan.key_advice_ar}</div>
      <button class="speak-plan-btn" data-plan-id="${plan.plan_id}">
        🔊 اسمع شرح المحصول ده
      </button>
    `;
    plansList.appendChild(card);
  });

  // Attach individual TTS playback buttons
  document.querySelectorAll('.speak-plan-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const pId = e.currentTarget.getAttribute('data-plan-id');
      const targetPlan = plans.find((p) => p.plan_id === pId);
      if (targetPlan) {
        const script = `محصول ${targetPlan.primary_crop_ar}. بيحقق صافي ربح ${Math.round(targetPlan.metrics.net_profit_egp_per_feddan)} جنيه للفدان. وبيستهلك ${Math.round(targetPlan.metrics.water_demand_m3_per_feddan)} متر مكعب مية. نصيحتنا: ${targetPlan.key_advice_ar}. ده تقدير استرشادي مش ضمان.`;
        speakArabic(script);
      }
    });
  });

  recommendationsContainer.style.display = 'flex';
  micStatus.innerText = 'تم حساب الاختيارات';
  recommendationsContainer.scrollIntoView({ behavior: 'smooth' });
}

// Tap Fallback Form Submission
tapFallbackForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const location = document.getElementById('tapLocation').value;
  const feddans = parseFloat(document.getElementById('tapArea').value);
  const water = document.getElementById('tapWater').value;

  const coordsMap = {
    'Kafr El-Sheikh': { latitude: 31.11, longitude: 30.94 },
    Minya: { latitude: 28.11, longitude: 30.75 },
    'New Valley': { latitude: 25.45, longitude: 30.55 },
  };

  const payload = {
    location_name: location,
    coordinates: coordsMap[location] || { latitude: 31.11, longitude: 30.94 },
    area: { feddans: feddans, qirats: 0 },
    water_source: water,
    irrigation_method: 'surface_flood',
  };

  micStatus.innerText = 'بنحسب الاختيارات لأرضك...';

  try {
    const res = await fetch(`${API_BASE}/api/recommendations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    renderRecommendations(data);
    speakArabic(`يا حاج، حسبنا لك الاختيارات لأرضك في ${data.farm_location}. تقدر تضغط على أي كارت عشان تسمع تفاصيله.`);
  } catch (err) {
    console.error('Fallback submission error:', err);
    alert('تعذر الاتصال بالخادم.');
  }
});

// Event Listeners
micBtn.addEventListener('click', () => {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
});

btnConfirmYes.addEventListener('click', () => handleConfirmation(true));
btnConfirmNo.addEventListener('click', () => handleConfirmation(false));

// Load speech voices
if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices();
  };
}

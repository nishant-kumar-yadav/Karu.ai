/**
 * KARU.ai — Frontend Application Logic
 */

// Global State
const state = {
  phone: "",
  artisanId: localStorage.getItem("karu_artisan_id") || "",
  profile: null,
  photos: [],
  microphoneStream: null,
  mediaRecorder: null,
  audioChunks: [],
  cardCount: 3,
};

// DOM Elements
const els = {
  // Screens
  screens: {
    welcome: document.getElementById("screen-welcome"),
    otp: document.getElementById("screen-otp"),
    profile: document.getElementById("screen-profile"),
    dashboard: document.getElementById("screen-dashboard"),
    results: document.getElementById("screen-results"),
  },

  // Auth Inputs
  inpPhone: document.getElementById("inp-phone"),
  btnRegister: document.getElementById("btn-register"),
  otpPhoneSpan: document.getElementById("otp-phone"),
  otpBoxes: document.querySelectorAll(".otp-digit"),
  btnVerify: document.getElementById("btn-verify"),

  // Profile Setup
  inpName: document.getElementById("inp-name"),
  inpDistrict: document.getElementById("inp-district"),
  inpState: document.getElementById("inp-state"),
  inpUpi: document.getElementById("inp-upi"),
  btnCreateProfile: document.getElementById("btn-create-profile"),
  craftChips: document.querySelectorAll("#craft-chips .chip"),
  inpProfilePhoto: document.getElementById("inp-profile-photo"),
  profilePhotoPreview: document.getElementById("profile-photo-preview"),
  profilePhotoPlaceholder: document.getElementById("profile-photo-placeholder"),

  // Dashboard Header
  dashGreeting: document.getElementById("dashboard-greeting"),
  dashName: document.getElementById("dash-name"),
  dashLocation: document.getElementById("dash-location"),
  dashMonogram: document.getElementById("dash-monogram"),
  dashBadge: document.getElementById("dash-badge"),
  dashPercent: document.getElementById("dash-percent"),
  dashProgress: document.getElementById("dash-progress"),

  // Dashboard Stats
  heroStatListings: document.getElementById("hero-stat-listings"),
  heroStatProfile: document.getElementById("hero-stat-profile"),
  statListings: document.getElementById("stat-listings"),

  // Studio Upload
  uploadTrigger: document.getElementById("upload-trigger"),
  inpPhotos: document.getElementById("inp-photos"),
  photoPreviewArea: document.getElementById("photo-preview"),

  // Studio Inputs
  inpVoice: document.getElementById("inp-voice"),
  btnMic: document.getElementById("btn-mic"),
  langButtons: document.querySelectorAll("#voice-lang-row button"),
  inpProdType: document.getElementById("inp-prodtype"),
  cardCountButtons: document.querySelectorAll("#card-count-row button"),
  btnGenerate: document.getElementById("btn-generate"),

  // Results Screen
  resultsGrid: document.querySelector(".results-cards-grid"),
  trustScoreCircle: document.querySelector(".trust-score-circle"),
  trustLabel: document.querySelector(".trust-label"),
  priceDisplay: document.querySelector(".insight-price-display"),
  seoKeywords: document.querySelector(".seo-tags"),
  heritageStory: document.querySelector(".heritage-story-text"),

  // Navigation
  mainNav: document.getElementById("main-nav"),
  noPastProducts: document.getElementById("no-past-products"),

  // Results Actions
  btnShareWhatsapp: document.getElementById("btn-share-whatsapp"),
  btnShareInstagram: document.getElementById("btn-share-instagram"),
  btnDownloadZip: document.getElementById("btn-download-zip"),
  btnBackToStudio: document.getElementById("btn-back-studio")
};

let currentResultProductId = null;

// ==============================================
// INIT
// ==============================================
async function init() {
  attachListeners();

  if (state.artisanId) {
    try {
      const res = await fetch(`/profile/${state.artisanId}`);
      if (res.ok) {
        state.profile = await res.json();
        populateDashboard();
        await showDashboard(); // This will unhide the nav
      } else {
        throw new Error("Invalid session");
      }
    } catch (e) {
      localStorage.removeItem("karu_artisan_id");
      state.artisanId = "";
      if (els.mainNav) els.mainNav.style.display = "none";
      showScreen("welcome");
    }
  } else {
    if (els.mainNav) els.mainNav.style.display = "none";
    showScreen("welcome");
  }
}

async function showDashboard() {
  if (els.mainNav) els.mainNav.style.display = "flex"; // Reveal nav on login
  showScreen("dashboard");
}

function showScreen(screenKey) {
  Object.values(els.screens).forEach(s => s?.classList.remove("active"));
  const target = els.screens[screenKey];
  if (target) {
    target.classList.add("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

// ==============================================
// AUTH FLOW
// ==============================================
function attachListeners() {
  // Step 1: Request OTP
  els.btnRegister?.addEventListener("click", async () => {
    const rawPhone = els.inpPhone.value.replace(/\D/g, "");
    if (rawPhone.length < 10) return alert("Enter a valid 10-digit number.");
    
    state.phone = "+91" + rawPhone;
    
    const oldHtml = els.btnRegister.innerHTML;
    els.btnRegister.innerHTML = "<i class='bi bi-arrow-repeat spin'></i> Sending...";
    els.btnRegister.disabled = true;

    try {
      const res = await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: state.phone }),
      });
      if (!res.ok) throw new Error("Registration failed");
      
      els.otpPhoneSpan.textContent = state.phone;
      showScreen("otp");
      els.otpBoxes[0]?.focus();
    } catch(e) {
      alert("Error sending OTP");
    } finally {
      els.btnRegister.innerHTML = oldHtml;
      els.btnRegister.disabled = false;
    }
  });

  // OTP inputs auto-advance
  els.otpBoxes?.forEach((box, i) => {
    box.addEventListener("input", (e) => {
      if (e.target.value && i < 5) els.otpBoxes[i + 1].focus();
    });
    box.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !e.target.value && i > 0) {
        els.otpBoxes[i - 1].focus();
      }
    });
  });

  // Step 2: Verify OTP
  els.btnVerify?.addEventListener("click", async () => {
    const code = Array.from(els.otpBoxes).map(b => b.value).join("");
    if (code.length < 6) return alert("Enter 6-digit OTP");

    const oldHtml = els.btnVerify.innerHTML;
    els.btnVerify.innerHTML = "<i class='bi bi-arrow-repeat spin'></i> Verifying...";
    els.btnVerify.disabled = true;

    try {
      const res = await fetch("/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: state.phone, otp: code }),
      });
      
      const data = await res.json();
      
      if (res.ok) {
        state.artisanId = data.artisan_id;
        localStorage.setItem("karu_artisan_id", state.artisanId);
        
        if (data.is_new) {
          showScreen("profile");
        } else {
          // fetch profile
          const pRes = await fetch(`/profile/${state.artisanId}`);
          if (pRes.ok) {
            state.profile = await pRes.json();
            populateDashboard();
            await showDashboard();
          }
        }
      } else {
        alert("Invalid OTP");
      }
    } catch(e) {
      alert("Verification failed");
    } finally {
      els.btnVerify.innerHTML = oldHtml;
      els.btnVerify.disabled = false;
    }
  });

  // Step 3: Profile Photo Preview
  els.inpProfilePhoto?.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      const reader = new FileReader();
      reader.onload = (e) => {
        els.profilePhotoPreview.src = e.target.result;
        els.profilePhotoPreview.classList.remove("hidden");
        els.profilePhotoPlaceholder.classList.add("hidden");
      };
      reader.readAsDataURL(e.target.files[0]);
    }
  });

  // Profile Craft Selection
  let selectedCraft = "generic";
  els.craftChips?.forEach(chip => {
    chip.addEventListener("click", () => {
      els.craftChips.forEach(c => c.classList.remove("selected"));
      chip.classList.add("selected");
      selectedCraft = chip.dataset.val;
    });
  });

  // Create Profile
  els.btnCreateProfile?.addEventListener("click", async () => {
    if (!els.inpName.value.trim() || !els.inpDistrict.value.trim()) {
      return alert("Name and District are required.");
    }
    
    const formData = new FormData();
    const payload = {
      phone: state.phone,
      name: els.inpName.value.trim(),
      district: els.inpDistrict.value.trim(),
      state: els.inpState.value || "Other",
      craft_types: [selectedCraft],
      upi_id: els.inpUpi.value.trim(),
      preferred_language: "hi"
    };

    formData.append("profile_data", JSON.stringify(payload));
    
    if (els.inpProfilePhoto.files[0]) {
      formData.append("photo", els.inpProfilePhoto.files[0]);
    }

    const oldHtml = els.btnCreateProfile.innerHTML;
    els.btnCreateProfile.innerHTML = "<i class='bi bi-arrow-repeat spin'></i> Creating...";
    els.btnCreateProfile.disabled = true;

    try {
      const res = await fetch("/profile", {
        method: "POST",
        body: formData
      });
      
      if (res.ok) {
        state.profile = await res.json();
        populateDashboard();
        await showDashboard();
      } else {
        alert("Failed to create profile");
      }
    } catch(e) {
      alert("Error creating profile");
    } finally {
      els.btnCreateProfile.innerHTML = oldHtml;
      els.btnCreateProfile.disabled = false;
    }
  });

  // ==============================================
  // DASHBOARD STUDIO LOGIC
  // ==============================================
  
  // Product Photos Upload
  els.uploadTrigger?.addEventListener("click", () => {
    // Only trigger if clicking the box itself, not inner buttons
    els.inpPhotos.click();
  });
  
  els.dashBadge?.parentElement?.addEventListener("click", () => {
      fetch(\`/profile/\${state.artisanId}\`)
          .then(r => r.json())
          .then(data => {
              state.profile = data;
              populateDashboard();
          });
  });

  els.inpPhotos?.addEventListener("change", (e) => {
    const files = Array.from(e.target.files).slice(0, 5); // Max 5
    if (!files.length) return;
    
    state.photos = files;
    els.photoPreviewArea.innerHTML = "";
    
    files.forEach((file, index) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const div = document.createElement("div");
        div.className = "preview-thumbnail";
        div.innerHTML = \`
          <img src="\${ev.target.result}" alt="Product \${index + 1}">
          <button class="remove-btn" type="button" data-idx="\${index}">
            <i class="bi bi-x"></i>
          </button>
        \`;
        els.photoPreviewArea.appendChild(div);
      };
      reader.readAsDataURL(file);
    });
    
    // Hide placeholder, show preview
    els.uploadTrigger.querySelector(".upload-big-icon").style.display = "none";
    els.uploadTrigger.querySelector("h3").style.display = "none";
    els.uploadTrigger.querySelector("p").style.display = "none";
    els.uploadTrigger.querySelector(".upload-helper-pills").style.display = "none";
    els.photoPreviewArea.style.display = "flex";
  });
  
  els.photoPreviewArea?.addEventListener("click", (e) => {
    const btn = e.target.closest(".remove-btn");
    if (btn) {
      e.stopPropagation();
      const idx = parseInt(btn.dataset.idx);
      state.photos.splice(idx, 1);
      btn.parentElement.remove();
      
      if (state.photos.length === 0) {
        els.photoPreviewArea.style.display = "none";
        els.uploadTrigger.querySelector(".upload-big-icon").style.display = "flex";
        els.uploadTrigger.querySelector("h3").style.display = "block";
        els.uploadTrigger.querySelector("p").style.display = "block";
        els.uploadTrigger.querySelector(".upload-helper-pills").style.display = "flex";
      }
    }
  });

  // Language Selection
  let selectedLang = "hi-IN";
  els.langButtons?.forEach(btn => {
    btn.addEventListener("click", () => {
      els.langButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      selectedLang = btn.dataset.lang;
    });
  });

  // Card Count
  els.cardCountButtons?.forEach(btn => {
    btn.addEventListener("click", () => {
      els.cardCountButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.cardCount = parseInt(btn.dataset.count);
    });
  });

  // Mic Recording
  let isRecording = false;
  els.btnMic?.addEventListener("click", async () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  function startRecording() {
    isRecording = true;
    els.btnMic.classList.add("recording");
    els.btnMic.innerHTML = "<i class='bi bi-stop-fill'></i>";
    els.inpVoice.placeholder = "Listening... Speak clearly about your product.";
    // Simple mock behavior since we use text input for the AI right now
    // In a full implementation, you'd use MediaRecorder
    setTimeout(() => {
        if(isRecording) stopRecording();
    }, 5000);
  }

  function stopRecording() {
    isRecording = false;
    els.btnMic.classList.remove("recording");
    els.btnMic.innerHTML = "<i class='bi bi-mic-fill'></i>";
    // Mock recorded text
    if (!els.inpVoice.value) {
        els.inpVoice.value = "Yeh matka maine khud banaya hai. Ye pure clay ka hai. Bahut time laga isko banane mein.";
    }
  }

  // GENERATE ACTION
  els.btnGenerate?.addEventListener("click", async () => {
    if (state.photos.length === 0) {
      return alert("Please upload at least 1 product photo.");
    }

    const formData = new FormData();
    state.photos.forEach(file => formData.append("photos", file));
    
    formData.append("artisan_id", state.artisanId);
    formData.append("voice_description", els.inpVoice.value.trim());
    formData.append("product_type", els.inpProdType.value.trim());
    formData.append("preferred_language", selectedLang.split("-")[0]);
    formData.append("num_cards", state.cardCount);

    const oldHtml = els.btnGenerate.innerHTML;
    els.btnGenerate.innerHTML = "<i class='bi bi-stars spin'></i><span>Generating AI Assets...</span>";
    els.btnGenerate.disabled = true;

    try {
      // The backend combines everything into one phase
      const genRes = await fetch("/products/generate", {
        method: "POST",
        body: formData
      });
      
      if (!genRes.ok) throw new Error("Generation failed");
      
      const productData = await genRes.json();
      currentResultProductId = productData.product_id;
      
      // We need profile info updated for trust score + dashboard stats
      const pRes = await fetch(\`/profile/\${state.artisanId}\`);
      if (pRes.ok) {
        state.profile = await pRes.json();
      }
      
      populateResults(productData);
      showScreen("results");
      
    } catch(e) {
      alert("Failed to generate listing. " + e.message);
    } finally {
      els.btnGenerate.innerHTML = oldHtml;
      els.btnGenerate.disabled = false;
    }
  });
  
  // Results Actions
  els.btnBackToStudio?.addEventListener("click", () => {
    // Refresh dashboard stats
    populateDashboard();
    
    // Reset studio
    state.photos = [];
    els.photoPreviewArea.innerHTML = "";
    els.photoPreviewArea.style.display = "none";
    els.uploadTrigger.querySelector(".upload-big-icon").style.display = "flex";
    els.uploadTrigger.querySelector("h3").style.display = "block";
    els.uploadTrigger.querySelector("p").style.display = "block";
    els.uploadTrigger.querySelector(".upload-helper-pills").style.display = "flex";
    
    els.inpVoice.value = "";
    els.inpProdType.value = "";
    
    showScreen("dashboard");
  });
  
  els.btnShareWhatsapp?.addEventListener("click", async () => {
      if(!currentResultProductId) return;
      const res = await fetch(\`/share/whatsapp/\${currentResultProductId}\`);
      const data = await res.json();
      if(data.deep_link) {
          window.open(data.deep_link, '_blank');
      } else {
          alert("WhatsApp sharing ready. Copy caption:\n\n" + data.caption);
      }
  });

  els.btnShareInstagram?.addEventListener("click", async () => {
      if(!currentResultProductId) return;
      const res = await fetch(\`/share/instagram/\${currentResultProductId}\`);
      const data = await res.json();
      alert("Caption copied to clipboard ready for Instagram!\n\n" + data.caption.substring(0, 100) + "...");
  });
}

// ==============================================
// POPULATE DASHBOARD
// ==============================================
function populateDashboard() {
  const p = state.profile;
  if (!p) return;

  const names = p.name.split(" ");
  els.dashGreeting.textContent = \`Good Evening, \${names[0]}\`;
  
  els.dashName.textContent = p.name;
  els.dashLocation.textContent = \`\${p.district}, \${p.state}\`;
  
  if (p.monogram_url) {
    els.dashMonogram.src = p.monogram_url + "?t=" + new Date().getTime();
  } else if (p.profile_photo_url) {
    els.dashMonogram.src = p.profile_photo_url;
  }
  
  // Stats
  els.heroStatListings.textContent = p.product_count || 0;
  els.statListings.textContent = p.product_count || 0;
  
  // Profile completion calc (mock)
  let complete = 40;
  if (p.profile_photo_url) complete += 20;
  if (p.upi_id) complete += 15;
  if (p.heritage_story) complete += 25;
  
  els.heroStatProfile.textContent = complete + "%";
  els.dashPercent.textContent = complete;
  els.dashProgress.style.width = complete + "%";
  
  // Badge logic matching backend
  let badgeLabel = "New Artisan";
  let badgeClass = "badge-gold";
  
  if (p.trust_score >= 85 && p.product_count >= 25) {
      badgeLabel = "💎 Heritage Master";
  } else if (p.trust_score >= 75 && p.product_count >= 15) {
      badgeLabel = "🥇 Master Artisan";
  } else if (p.product_count >= 5) {
      badgeLabel = "🥈 Active Artisan";
      badgeClass = "badge-teal";
  }
  
  els.dashBadge.innerHTML = \`<i class="bi bi-patch-check"></i> \${badgeLabel}\`;
  els.dashBadge.className = \`badge \${badgeClass}\`;
}

// ==============================================
// POPULATE RESULTS
// ==============================================
function populateResults(data) {
  // 1. Cards
  els.resultsGrid.innerHTML = "";
  data.cards.forEach(card => {
    const div = document.createElement("div");
    div.className = "result-card-item";
    div.innerHTML = \`
      <img src="/output/\${card.filename}" alt="\${card.card_type}">
      <div class="result-card-label">\${formatCardType(card.card_type)}</div>
    \`;
    els.resultsGrid.appendChild(div);
  });
  
  // 2. Trust Score
  const score = Math.round(data.trust_score);
  els.trustScoreCircle.innerHTML = \`<strong>\${score}</strong><span>/100</span>\`;
  
  if (score >= 80) {
      els.trustLabel.innerHTML = '<i class="bi bi-shield-fill-check"></i> High Authenticity';
      els.trustScoreCircle.style.background = 'radial-gradient(circle at center, rgba(102,187,106,0.1), transparent)';
  } else if (score >= 50) {
      els.trustLabel.innerHTML = '<i class="bi bi-shield-exclamation"></i> Medium Verification';
  } else {
      els.trustLabel.innerHTML = '<i class="bi bi-shield-x"></i> Needs Verification';
  }
  
  // 3. Pricing
  const parsed = data.parsed_data;
  if (parsed.price_recommended) {
      els.priceDisplay.innerHTML = \`
          <span class="currency">₹</span><span class="amount">\${parsed.price_recommended}</span>
          <br><small style="font-size: 0.6em; font-weight: 500; color: #7e8ca4;">Recommended Retail</small>
      \`;
  } else if (parsed.price_artisan_asked) {
      els.priceDisplay.innerHTML = \`
          <span class="currency">₹</span><span class="amount">\${parsed.price_artisan_asked}</span>
          <br><small style="font-size: 0.6em; font-weight: 500; color: #7e8ca4;">Artisan Asked</small>
      \`;
  } else {
      els.priceDisplay.innerHTML = \`<span class="amount" style="font-size: 1.2rem">AI Analyzing...</span>\`;
  }
  
  // 4. SEO Tags
  els.seoKeywords.innerHTML = "";
  if (parsed.seo_keywords && parsed.seo_keywords.length > 0) {
      parsed.seo_keywords.slice(0, 6).forEach(kw => {
          const span = document.createElement("span");
          span.className = "seo-tag";
          span.textContent = kw;
          els.seoKeywords.appendChild(span);
      });
  } else {
      els.seoKeywords.innerHTML = "<span class='seo-tag'>handmade</span><span class='seo-tag'>artisan</span>";
  }
  
  // 5. Heritage Story
  els.heritageStory.innerHTML = parsed.description || parsed.heritage_story || "A beautifully handcrafted original piece.";
}

function formatCardType(type) {
  const map = {
      hero: "Hero Shot",
      features: "Features",
      lifestyle: "Lifestyle",
      macro: "Detail View",
      heritage: "Heritage Scene"
  };
  return map[type] || type;
}

// Start app
init();

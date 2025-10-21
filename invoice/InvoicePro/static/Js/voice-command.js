// ----- Check browser support -----
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (!SpeechRecognition) {
    console.error("Speech Recognition இந்த browserல் support இல்லை");
} else {
    const recognition = new SpeechRecognition();
    recognition.lang = "ta-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = true; // Keeps listening continuously

    let isListening = false;
    let voiceModal;

    document.addEventListener("DOMContentLoaded", () => {
        const modalEl = document.getElementById("voiceCommandModal");
        if (modalEl) voiceModal = new bootstrap.Modal(modalEl);

        const voiceBtn = document.getElementById("voiceAssistBtn");
        if (voiceBtn) {
            voiceBtn.addEventListener("click", () => {
                if (!isListening) {
                    recognition.start();
                    isListening = true;
                    console.log("🎤 Voice recognition தொடங்கியது");
                    if (voiceModal) voiceModal.show();
                    document.body.style.overflow = "hidden"; // Disable scroll during recording
                } else {
                    recognition.stop();
                    closeModal();
                }
            });
        }
    });

    // ------------------- MAIN RECOGNITION HANDLER -------------------
    recognition.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
        console.log("நீங்கள் சொன்னது:", transcript);

        // ----- Stop command -----
        if (["நிறுத்து", "முடிந்தது", "ஆமாம்", "stop"].includes(transcript)) {
            recognition.stop();
            closeModal();
            console.log("🎤 Voice session முடிந்தது");
            return;
        }

        // ----- Client selection -----
        if (transcript.startsWith("கிளையன்ட் ")) {
            const name = transcript.replace("கிளையன்ட்", "").trim();
            const clientSelect = document.getElementById("client_id");
            if (clientSelect) {
                for (let i = 0; i < clientSelect.options.length; i++) {
                    if (clientSelect.options[i].text.toLowerCase().includes(name)) {
                        clientSelect.value = clientSelect.options[i].value;
                        clientSelect.dispatchEvent(new Event('change'));
                        console.log(`✅ Client set to: ${clientSelect.options[i].text}`);
                        break;
                    }
                }
            }
        }

        // ----- Add item -----
        if (transcript.includes("ஐடம் சேர்க்க") || transcript.includes("ஐட்டம் சேர்க்க")) {
            console.log("🎤 Voice trigger detected → ஐடம் சேர்க்க");

            let itemsText = transcript
                .replace("ஐடம் சேர்க்க", "")
                .replace("ஐட்டம் சேர்க்க", "")
                .trim();

            console.log("🧾 Raw item text:", itemsText);

            const items = itemsText.split(" மற்றும் ").map(t => t.trim()).filter(Boolean);
            console.log("🧾 Items parsed:", items);

            items.forEach(itemText => {
                const parts = itemText.split(" அளவு ");
                const description = parts[0]?.trim() || "பொருள்";
                let quantity = 1, rate = 0;

                if (parts[1]) {
                    const qParts = parts[1].split(" விலை ");
                    const qtyText = qParts[0]?.trim() || "1";
                    quantity = parseInt(qtyText) || tamilTextToNumber(qtyText) || 1;

                    if (qParts[1]) {
                        const rateText = qParts[1].trim();
                        let base = parseFloat(rateText.replace(/[^\d.]/g, "")) || tamilTextToNumber(rateText) || 0;

                        if (rateText.includes("ஆயிரம்")) base *= 1000;
                        else if (rateText.includes("நூறு")) base *= 100;
                        else if (rateText.includes("லட்சம்")) base *= 100000;

                        rate = base;
                    }
                }

                // ✅ Add the item dynamically
                if (typeof addItemRow === "function") {
                    addItemRow({ description, quantity, unit_price: rate });
                    console.log(`🛒 Item சேர்க்கப்பட்டது: ${description}, Qty: ${quantity}, Rate: ${rate}`);
                    // Recalculate after add
                    calculateItemAmounts();
                    if (typeof updateInvoiceSummary === "function") updateInvoiceSummary();
                } else {
                    console.warn("⚠️ addItemRow() function not found.");
                }
            });
        }

        // ----- Save invoice -----
        if (transcript === "சேமி") {
            document.getElementById("saveInvoiceBtn")?.click();
        }

        // ----- Preview invoice -----
        if (transcript === "பார்க்க") {
            document.getElementById("previewBtn")?.click();
        }
    };

    // ------------------- ERROR HANDLER -------------------
    recognition.onerror = (event) => {
        console.error("Recognition பிழை:", event.error);
        if (event.error === "no-speech" && isListening) {
            console.log("⏳ No speech detected — restarting recognition...");
            recognition.start();
        }
    };

    // ------------------- END HANDLER -------------------
    recognition.onend = () => {
        console.log("🎤 Recognition முடிந்தது");
        closeModal();

        if (isListening) {
            console.log("🔁 Restarting recognition...");
            recognition.start();
        }
    };

    // ------------------- HELPER FUNCTIONS -------------------

    // ✅ Calculate item row amount (Qty × Rate) for your current table
    function calculateItemAmounts() {
        document.querySelectorAll("tr.invoice-item").forEach(row => {
            const qtyField = row.querySelector("td:nth-child(3)"); // Qty column
            const rateField = row.querySelector("td:nth-child(5)"); // Rate column
            const amountField = row.querySelector("td:nth-child(7)"); // Amount column
             const amountField1 = row.querySelector(".amount");


            const qty = parseFloat(qtyField?.textContent || 0);
            const rate = parseFloat(rateField?.textContent || 0);

            if (amountField) {
                const amount = qty * rate;
                amountField.textContent = `₹${amount.toFixed(2)}`;
            }
        });

        if (typeof updateInvoiceSummary === "function") updateInvoiceSummary();
    }

    // ✅ Modal close cleanup
    function closeModal() {
        const modalEl = document.getElementById("voiceCommandModal");
        if (modalEl) {
            let modal = bootstrap.Modal.getInstance(modalEl);
            if (!modal) modal = new bootstrap.Modal(modalEl);
            modal.hide();
        }

        // Remove leftover backdrops and restore scroll
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        document.body.style.overflow = "auto";
        isListening = false;
    }

    // ✅ Tamil number conversion helper
    function tamilTextToNumber(text) {
        const map = {
            "பூஜ்யம்": 0, "ஒன்று": 1, "இரண்டு": 2, "மூன்று": 3,
            "நான்கு": 4, "ஐந்து": 5, "ஆறு": 6, "ஏழு": 7,
            "எட்டு": 8, "ஒன்பது": 9, "பத்து": 10, "ஆயிரம்": 1000
        };

        let num = 0;
        const words = text.split(" ");
        words.forEach(word => {
            if (!isNaN(word)) num += parseInt(word);
            else if (map[word]) num += map[word];
        });

        return num || null;
    }
}

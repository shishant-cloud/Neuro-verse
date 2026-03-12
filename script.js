/* ================= TEXT FORMATTING ================= */
function format(command) {
    document.execCommand(command, false, null);
}

function setFont(fontName) {
    document.execCommand("fontName", false, fontName);
}

function setColor(color) {
    if (!color) return;
    document.execCommand("foreColor", false, color);
}

function newFile() {
    if (confirm("Are you sure? This will clear the entire document.")) {
        document.getElementById("page").innerHTML = "<p><br></p>";
    }
}

/* ================= TABLE GENERATOR ================= */
function createTablePrompt() {
    const rows = prompt("Enter number of rows:", "3");
    const cols = prompt("Enter number of columns:", "3");
    
    if (rows > 0 && cols > 0) {
        let tableHTML = `<table style="width: 100%; border-collapse: collapse; margin: 20px 0;"><tbody>`;
        for (let i = 0; i < rows; i++) {
            tableHTML += `<tr>`;
            for (let j = 0; j < cols; j++) {
                tableHTML += `<td style="border: 1px solid #cbd5e1; padding: 12px; min-width: 50px;">&nbsp;</td>`;
            }
            tableHTML += `</tr>`;
        }
        tableHTML += `</tbody></table><p><br></p>`;
        insertHTMLAtCursor(tableHTML);
    }
}

function insertHTMLAtCursor(html) {
    let sel = window.getSelection();
    if (sel.getRangeAt && sel.rangeCount) {
        let range = sel.getRangeAt(0);
        range.deleteContents();
        let el = document.createElement("div");
        el.innerHTML = html;
        let frag = document.createDocumentFragment(), node, lastNode;
        while ((node = el.firstChild)) { lastNode = frag.appendChild(node); }
        range.insertNode(frag);
    }
}

/* ================= THE STABLE PDF EXPORT ================= */
function exportPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF("p", "mm", "a4");
    const page = document.getElementById("page");

    // 1. Handle Tables specifically using autoTable
    const tables = page.querySelectorAll("table");
    if (tables.length > 0) {
        tables.forEach((table, index) => {
            doc.autoTable({
                html: table,
                startY: index === 0 ? 25 : doc.lastAutoTable.finalY + 10,
                theme: 'grid',
                styles: { fontSize: 10, cellPadding: 3 },
                headStyles: { fillColor: [22, 163, 74] } 
            });
        });
    }

    // 2. Handle Text (Simple and fast method)
    // We remove tables from the text extraction to avoid duplicate data
    let tempDiv = page.cloneNode(true);
    tempDiv.querySelectorAll("table").forEach(t => t.remove());
    const content = tempDiv.innerText || tempDiv.textContent;
    
    const lines = doc.splitTextToSize(content, 180);
    // If tables existed, we start text after tables, otherwise start at top
    let textStartY = tables.length > 0 ? doc.lastAutoTable.finalY + 15 : 20;
    
    doc.text(lines, 15, textStartY);

    // 3. Save directly
    doc.save("NeuroVerse_Document.pdf");
}





/* ================= ACCOUNT SECURITY LOGIC ================= */
function verifyAdminKey() {
    const MASTER_KEY = "NEURO-2026-X";
    const input = document.getElementById('admin-pk');
    const msg = document.getElementById('verify-msg');
    const passField = document.getElementById('new-password');
    const saveBtn = document.getElementById('final-save');

    console.log("Attempting to verify key..."); // Debugging line

    if (input.value === MASTER_KEY) {
        msg.innerText = "✓ Key Verified. You can now set your password.";
        msg.style.color = "#16a34a";
        
        passField.disabled = false;
        passField.style.background = "#ffffff";
        passField.style.cursor = "text";
        passField.placeholder = "Enter minimum 8 characters";
        
        saveBtn.disabled = false;
        saveBtn.style.opacity = "1";
        saveBtn.style.cursor = "pointer";
        
        input.style.borderColor = "#22c55e";
        input.readOnly = true; 
    } else {
        msg.innerText = "× Invalid Admin Key. Access Denied.";
        msg.style.color = "#ef4444";
        input.style.borderColor = "#ef4444";
    }
}
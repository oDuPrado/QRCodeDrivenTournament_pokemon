# QRCodeDrivenTournament

---

# **Tournament Manager**

Tournament Manager is a live tournament management system designed to facilitate reporting and tracking results in real-time. Using Flask for the backend and a dynamic frontend, it integrates QR codes for seamless table identification and offers a responsive design suitable for any device.

---

## **Features**

1 -Configure the directory containing the tournament's .tdf files.<br>

2- Run <code>main_1</code> locally to monitor changes, generate QR codes for the tables, and create a PDF with players' PINs.<br>

3 - <code>main_2</code> runs on the online server, receiving updates and displaying the data.<br>

4- Provide players with their PIN and ID (printed in the generated PDF) so they can report results on their respective <code>mesa.html</code> pages.<br>

5-With each vote, the system updates the status on <code>report.html</code>, showing finalized tables, pending votes, or divergences, all in real-time (polling every 5 seconds).

---

## **Tech Stack**

### **Languages and Frameworks**

- Python (Flask)
- HTML5, CSS3
- JavaScript

### **Utilities**

- QR Code generation
- Responsive CSS for optimized design

---

## **Getting Started**

### **Prerequisites**

Ensure Python is installed on your system. Use the following command to check:

```bash
python --version
```

### **Setup**

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tournament-manager.git
   ```
2. Navigate to the project directory:
   ```bash
   cd tournament-manager
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:

   ```bash
   python main.py
   ```

5. Access the app in your browser:
   ```
   https://<your-ip>.pythonanywhere.com
   ```

---

## **Usage**

### **1. Start the Tournament**

- Access the home page to initialize the tournament.
- Generate QR codes for tables.

### **2. Report Results**

- Use the QR codes to report results directly via mobile devices or any connected browser.

### **3. View Statistics**

- Monitor real-time statistics on the dashboard.
- Clear results to prepare for the next round.

---

Donations
If you find this project helpful and would like to support further development, consider donating:
https://picpay.me/marco.macedo10/0.5

---

## **Contributing**

Contributions are welcome! Follow these steps to contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -m "Add feature"`).
4. Push the branch (`git push origin feature-branch`).
5. Open a Pull Request.

---

## **License**

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


# QRCodeDrivenTournament

---

# **Tournament Manager**

Tournament Manager is a complete real-time tournament management system, designed to facilitate the monitoring and recording of results in a dynamic and efficient way. The system is designed to be responsive and accessible on any device, from desktops to smartphones.
The system updates along with TOM, showing real-time player information, and recording it in a Firestore database for stat analysis and integration with other systems.

---
## **Key Features**

1. Table and Match Management:
A) Creation and management of tournaments with support for different formats (round-robin, single elimination, etc.).
B) Real-time monitoring of match results.

2. QR Code for Table Identification:
A) Automatic generation of QR Codes for each gaming table.
B) Integration of QR Codes to facilitate the registration of matches directly by players or referees.

3. Responsive Web Platform:
A) Modern and intuitive interface, fully responsive to work on any device, including desktops, tablets and smartphones.

4. Admin Panel:
A) Tools for organizers to easily set up and manage tournaments, players, and tables.

5. Real-Time Updates:
A) Instant updates for players and admins via FFTP (with Flask).

6. Tournament History and Reports:
A) Detailed record of all tournaments held, allowing subsequent analysis.

B) Option to export reports in formats such as CSV or PDF.

7) Security and Authentication:
A) Robust authentication system using JWT (JSON Web Tokens).
B) Control of permissions for organizers, referees and players.

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
   git clone https://github.com/oDuPrado/QRCodeDrivenTournament_pokemon.git
   ```
2. Navigate to the project directory:
   ```bash
   cd QRCodeDrivenTournament_pokemon
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

## Donations

<div align="center">
  <p>If you find this project helpful and would like to support further development, consider donating:</p>
  <!-- Donation icon link for PicPay -->
  <a href="https://picpay.me/marco.macedo10/0.5" target="_blank">
    <img 
      src="https://img.shields.io/badge/Donate-PicPay-brightgreen?style=plastic&logo=amazonpay&logoColor=white" 
      alt="Donate with PicPay" 
      height="36"
    />
  </a>
</div>

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


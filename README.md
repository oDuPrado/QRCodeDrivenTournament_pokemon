# QRCodeDrivenTournament

---

# **Tournament Manager**

Tournament Manager is a live tournament management system designed to facilitate reporting and tracking results in real-time. Using Flask for the backend and a dynamic frontend, it integrates QR codes for seamless table identification and offers a responsive design suitable for any device.

---

## **Features**

- **Real-Time Updates**: WebSocket integration for instant updates during the tournament.
- **QR Code Support**: Unique QR codes for each table to simplify reporting.
- **Responsive Design**: Works on both desktop and mobile devices.
- **Dynamic Rounds**: Manage and report table outcomes for each round.
- **Statistics Dashboard**: Displays detailed player statistics and match outcomes.
- **Popup Reports**: Dedicated windows for reviewing results by round.

---

## **Tech Stack**

### **Languages and Frameworks**

- Python (Flask)
- HTML5, CSS3
- JavaScript

### **Utilities**

- QR Code generation
- WebSocket for live communication
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
   http://<your-ip>:5000
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


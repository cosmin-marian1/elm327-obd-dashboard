# Interfata OBD-II pentru ELM327 Bluetooth

Aplicatie desktop pentru monitorizarea si diagnosticarea unui autovehicul
prin OBD-II, folosind un adaptor ELM327 conectat prin port serial.

![interfata](https://imgur.com/W4K0Kqg)

## Functii

- monitorizare live pentru 31 de PID-uri OBD-II;
- actualizare progresiva a valorilor, fara blocarea interfetei;
- citire VIN si decodare WMI, producator, tara, an si serie;
- citire si stergere coduri DTC;
- reconectare automata dupa pierderea conexiunii;
- gauge-uri paginate si grafic RPM;
- logging CSV in folderul proiectului;
- testare cu emulator ELM327.

Interfata grafica in Python pentru un adaptor OBD-II bazat pe chipset ELM327,
conectat prin Bluetooth (profil SPP). Afiseaza in timp real RPM, viteza,
temperatura lichidului de racire, sarcina motorului, pozitia acceleratiei,
temperatura aerului de admisie, voltajul bateriei si nivelul de combustibil,
plus citire/stergere coduri de eroare (DTC) si logging in CSV.

## Arhitectura

```
obd_interface/
├── connection/
│   └── serial_connection.py   # dialog brut cu ELM327 peste port serial
├── protocol/
│   ├── pids.py                 # definitii PID (formule de conversie SAE J1979)
│   ├── parser.py                # parsare raspunsuri brute + decodare DTC
│   └── elm327.py                # interfata de nivel inalt (init, query, DTC)
├── workers/
│   └── poller.py                # QThread care interogheaza periodic ELM327
├── gui/
│   ├── gauge_widget.py           # cadran circular custom (QPainter)
│   └── main_window.py             # fereastra principala, leaga tot
├── storage/
│   └── data_logger.py             # logging in CSV
└── main.py                         # punct de intrare
```

Fluxul de date e intr-un singur sens: `PollerWorker` ruleaza pe un thread
separat (ca sa nu inghete GUI-ul cat timp astepti raspunsuri de la ELM327),
si comunica cu fereastra principala exclusiv prin semnale Qt. Portul serial
e atins DOAR de acest thread - orice actiune ceruta din GUI (citire/stergere
DTC) se face printr-un flag, nu printr-un apel direct, ca sa nu existe doua
thread-uri care scriu simultan pe acelasi port.

## Instalare

```bash
python -m venv venv
pip install -r requirements.txt
```

In PowerShell, mediul virtual poate fi activat cu:

```powershell
.\venv\Scripts\Activate.ps1
```

Necesita Python 3.11+ (foloseste `X | None` in type hints).

## Tutorial de utilizare

### 1. Instalarea pe Windows

Deschide PowerShell in folderul proiectului si creeaza mediul virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Daca PowerShell blocheaza activarea scriptului, ruleaza temporar:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

### 2. Pornirea cu emulatorul

Emulatorul permite testarea fara autovehicul. Cu o pereche de porturi virtuale
com0com, emulatorul si aplicatia trebuie sa foloseasca porturi opuse. In
configuratia folosita la testare:

```text
Emulator: COM10
Aplicatie: COM11
```

Porneste emulatorul in primul terminal. Comanda exacta depinde de instalarea
emulatorului, dar forma uzuala este:

```powershell
python -m pip install ELM327-emulator
python -m elm
```

In al doilea terminal porneste aplicatia:

```powershell
python main.py --port COM11
```

Nu deschide acelasi port in ambele programe. Daca apare `Access is denied`,
inchide instantele vechi ale simulatorului sau aplicatiei si verifica porturile
virtuale disponibile. O alternativa este perechea `COM3`/`COM4` sau orice alta
pereche configurata de com0com.

### 3. Pornirea cu un adaptor real

1. Conecteaza adaptorul ELM327 in mufa OBD-II.
2. Pune contactul masinii.
3. Imperecheaza adaptorul Bluetooth din Windows.
4. Identifica portul COM creat de conexiunea Bluetooth.
5. Instaleaza dependentele si porneste aplicatia cu acel port:

```powershell
python main.py --port COM4
```

La conectare, aplicatia initializeaza adaptorul, citeste VIN-ul, identifica
PID-urile suportate si incepe monitorizarea. Nu toate autovehiculele suporta
aceiasi parametri.

### 4. Folosirea interfetei

- **Statusul** arata daca aplicatia este conectata la ELM327.
- **VIN** afiseaza identificatorul vehiculului si informatiile decodabile.
- **Gauge-urile** afiseaza valorile live, cum ar fi RPM, viteza si temperaturi.
- **Paginile** permit navigarea intre toate gauge-urile disponibile.
- **Citeste DTC** trimite comanda OBD-II `03` si afiseaza erorile memorate.
- **Sterge DTC** trimite comanda `04`, dupa confirmare.
- **Porneste logging CSV** creeaza un fisier nou in folderul `logs`.
- La oprirea logging-ului, aplicatia afiseaza calea fisierului salvat.
- Graficul din partea de jos afiseaza evolutia RPM in timp.

### 5. Parametrii si actualizarile

Aplicatia interogheaza PID-urile pe rand si actualizeaza fiecare gauge imediat
dupa primirea raspunsului. Astfel interfata ramane fluida. ECU-ul este intrebat
mai intai ce PID-uri suporta, iar cele indisponibile sunt ascunse.

### 6. Logging si fisierele rezultate

Fisierele CSV sunt salvate in:

```text
logs/obd_log_YYYYMMDD_HHMMSS.csv
```

Coloanele contin timestamp-ul si valorile parametrilor cititi. Folderul este
calculat din locatia proiectului, deci rezultatul nu depinde de directorul din
care este pornita comanda.

### 7. Probleme frecvente

**`Access is denied` la portul COM**  
Portul este ocupat. Inchide emulatorul, aplicatia sau orice monitor serial si
foloseste capatul opus al perechii virtuale.

**`Niciun cod de eroare stocat`**  
ECU-ul nu are DTC-uri stocate sau emulatorul raspunde cu `43 00`. Este un
raspuns normal, nu o eroare a interfetei.

**VIN indisponibil**  
Vehiculul poate sa nu suporte Mode 09 PID 02 sau adaptorul poate sa nu fi
raspuns. Cu simulatorul, verifica sa fie folosit portul opus si emulatorul sa
fie repornit.

**Aplicatia nu se conecteaza**  
Verifica portul, contactul masinii, conexiunea Bluetooth si faptul ca ruleaza
o singura instanta a aplicatiei.

## Teste

Pentru testele automate, instaleaza dependentele si ruleaza:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

Testele verifica formule PID, raspunsuri invalide, DTC, VIN si cadre cu header
CAN. Emulatorul furnizeaza date simulate pentru dezvoltare fara autovehicul.

## Note tehnice / capcane intalnite in dezvoltare

- **Timeout-ul pyserial**: daca dai acelasi timeout portului serial (nivel
  jos) si buclei tale de "citeste pana la prompt" (nivel inalt), un singur
  `read()` poate consuma tot bugetul de timp dintr-o data, si bucla de retry
  nu mai apuca sa se execute. Solutia: timeout mic (0.1s) pe port, timeout-ul
  real gestionat separat, in bucla proprie.
- **DTC prin flag, nu prin apel direct**: portul serial nu e thread-safe;
  orice cerere din GUI catre ELM327 trece printr-un flag citit de thread-ul
  de polling, nu printr-un apel concurent.
- **Nu toate ECU-urile suporta toate PID-urile** - `query_many()` ignora
  PID-urile care esueaza in loc sa opreasca tot ciclul de citire.

## Extensii posibile pentru raportul de practica

- Suport pentru mode 02 (freeze frame data la momentul unei erori)
- Replay al unei sesiuni CSV inregistrate anterior (util pentru demo fara
  masina la prezentare)
- Auto-detectare a portului `/dev/rfcomm*` in loc de specificare manuala
- Reconectare automata daca legatura Bluetooth se intrerupe in timpul rularii

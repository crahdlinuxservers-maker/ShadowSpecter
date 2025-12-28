# 🔍 ShadowSpecter Ultimate

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

<p align="center">
  <img src="logo.png" alt="ShadowSpecter Logo" width="200"/>
</p>

**ShadowSpecter** to zaawansowane narzędzie OSINT (Open Source Intelligence) do skanowania i wyszukiwania nazw użytkowników na wielu platformach internetowych. Zbudowane z nowoczesnym interfejsem GUI i asynchronicznym silnikiem skanowania.

## ✨ Funkcje

### 🚀 Główna Funkcjonalność
- **Skanowanie wielu serwisów** — Skanuj nazwy użytkowników na setkach stron jednocześnie
- **Silnik asynchroniczny** — Wysokowydajne skanowanie z użyciem `aiohttp`
- **Wykrywanie fałszywych pozytywów** — Inteligentna weryfikacja redukująca błędne wyniki
- **Baza danych SQLite** — Trwała historia skanowań z pełnym śledzeniem wyników

### 🎨 Nowoczesny Interfejs Użytkownika
- **GUI CustomTkinter** — Piękny, nowoczesny interfejs z płynnymi animacjami
- **Wiele motywów** — Jasny, Ciemny i Ghost z przełączaniem w czasie rzeczywistym
- **Responsywny design** — Skalowalne okno z adaptacyjnym układem
- **Animowany ekran startowy** — Profesjonalny ekran ładowania ze spinnerem

### 📊 Zarządzanie Wynikami
- **Tabela wyników TreeView** — Sortowalne kolumny z kolorowymi wskaźnikami statusu
- **Zaawansowane filtrowanie** — Filtruj po statusie (Znalezione/Nieznalezione) i tekście
- **Menu kontekstowe** — Kliknij prawym przyciskiem, aby skopiować URL, otworzyć w przeglądarce lub skopiować wiersz
- **Eksport CSV** — Eksportuj przefiltrowane wyniki do formatu CSV

### ⚙️ Opcje Konfiguracji
- **Kontrola współbieżności** — Dostosuj liczbę równoległych wątków (1-100)
- **Timeout żądań** — Konfigurowalny timeout (5-60 sekund)
- **Tryb żądań** — Obsługa żądań HEAD lub GET
- **Konfiguracja User-Agent** — Własny ciąg User-Agent
- **Throttling żądań** — Opóźnienie per-host, aby uniknąć blokad
- **Weryfikacja SSL** — Opcja ignorowania błędów certyfikatów SSL

### 🛠️ Dodatkowe Narzędzia
- **Generator bazy serwisów** — Generuj 1000+ endpointów serwisów
- **Statystyki sesji** — Przeglądaj historię i statystyki skanowań
- **Sprawdzanie wycieków email** — Wyszukiwanie wycieków w stylu HIBP
- **Obsługa proxy** — Konfiguracja proxy HTTP/SOCKS (wkrótce)

## 📋 Wymagania

- Python 3.7 lub nowszy
- Zależności:
  ```
  customtkinter
  aiohttp
  pillow
  ```

## 🚀 Szybki Start

### 1. Sklonuj Repozytorium
```bash
git clone https://github.com/crahdlinuxservers-maker/ShadowSpecter.git
cd ShadowSpecter
```

### 2. Utwórz Środowisko Wirtualne (Zalecane)
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Zainstaluj Zależności
```bash
pip install customtkinter aiohttp pillow
```

### 4. Uruchom Aplikację
```bash
python shadow_specter.py
```

## 📁 Struktura Projektu

```
ShadowSpecter/
├── shadow_specter.py    # Główny plik aplikacji
├── services.json        # Baza endpointów serwisów
├── shadow_config.json   # Plik konfiguracyjny (generowany automatycznie)
├── shadow_specter.db    # Baza SQLite z historią skanowań
├── logo.png             # Logo aplikacji
├── LICENSE              # Plik licencji
└── README.md            # Ten plik
```

## 🎮 Użytkowanie

### Podstawowe Skanowanie
1. Uruchom aplikację
2. Wpisz nazwę użytkownika w polu wyszukiwania
3. Kliknij **▶ Start Scan**
4. Przeglądaj wyniki w tabeli (✓ = Znaleziono, ✗ = Nie znaleziono)

### Typy Wyszukiwania
- **Username** — Standardowe wyszukiwanie nazwy użytkownika
- **First Name** — Wyszukiwanie po imieniu
- **Last Name** — Wyszukiwanie po nazwisku
- **Email** — Wyszukiwanie adresu email

### Zarządzanie Serwisami
- **Add Service** — Dodaj własny serwis z wzorcem URL (użyj `{}` jako placeholder dla nazwy użytkownika)
- **Reload** — Przeładuj serwisy z `services.json`

### Filtrowanie Wyników
- Użyj dropdown **Filter** aby wyświetlić Wszystkie/Tylko znalezione/Tylko nieznalezione
- Użyj pola **Search** do filtrowania po nazwie serwisu lub URL

### Skróty Klawiszowe
| Skrót | Akcja |
|-------|-------|
| `Ctrl+O` | Importuj listę celów |
| `Ctrl+S` | Eksportuj wyniki do CSV |
| `Ctrl+C` | Kopiuj wybrany URL |
| `Ctrl+F` | Fokus na pole wyszukiwania |
| `Alt+F4` | Zamknij aplikację |

## ⚙️ Konfiguracja

Konfiguracja jest przechowywana w `shadow_config.json`:

```json
{
  "user_agent": "ShadowSpecter/Ultimate",
  "concurrency": 20,
  "per_host_delay": 0.5,
  "request_timeout": 12,
  "use_head": true,
  "respect_robots": false,
  "ignore_ssl": false,
  "anti_false": true,
  "mode": "Standard",
  "theme": "Light"
}
```

### Opcje Konfiguracji

| Opcja | Domyślnie | Opis |
|-------|-----------|------|
| `concurrency` | 20 | Liczba równoległych żądań |
| `per_host_delay` | 0.5 | Opóźnienie między żądaniami do tego samego hosta (sekundy) |
| `request_timeout` | 12 | Timeout żądania w sekundach |
| `use_head` | true | Używaj żądań HEAD (szybsze) |
| `anti_false` | true | Włącz wykrywanie fałszywych pozytywów |
| `ignore_ssl` | false | Pomijaj weryfikację certyfikatów SSL |
| `theme` | "Light" | Motyw UI (Light/Dark/Ghost) |

## 🔧 Dodawanie Własnych Serwisów

Edytuj `services.json` aby dodać własne serwisy:

```json
{
  "twitter": "https://twitter.com/{}",
  "github": "https://github.com/{}",
  "instagram": "https://www.instagram.com/{}",
  "reddit": "https://www.reddit.com/user/{}"
}
```

Użyj `{}` jako placeholder dla nazwy użytkownika.

## 📊 Schemat Bazy Danych

Aplikacja używa SQLite do przechowywania historii skanowań:

### Tabela Scans (Skanowania)
| Kolumna | Typ | Opis |
|---------|-----|------|
| id | INTEGER | Klucz główny |
| username | TEXT | Szukana nazwa użytkownika |
| started_at | TEXT | Znacznik czasu rozpoczęcia (format ISO) |

### Tabela Results (Wyniki)
| Kolumna | Typ | Opis |
|---------|-----|------|
| id | INTEGER | Klucz główny |
| scan_id | INTEGER | Odniesienie do tabeli scans |
| service | TEXT | Nazwa serwisu |
| url | TEXT | Pełny URL |
| ok | INTEGER | 1 = Znaleziono, 0 = Nie znaleziono |
| http | INTEGER | Kod statusu HTTP |
| reason | TEXT | Dodatkowe info (np. "anti_false") |
| scraped_at | TEXT | Znacznik czasu |

## 🎨 Motywy

### Light (Jasny)
Czysty, profesjonalny wygląd z niebieskimi akcentami.

### Dark (Ciemny)
Nowoczesny tryb ciemny ze zwiększonym kontrastem dla środowisk o słabym oświetleniu.

### Ghost (Duch)
Minimalistyczny motyw w odcieniach szarości dla pracy bez rozpraszaczy.

## 🖼️ Zrzuty Ekranu

### Ekran Główny
Nowoczesny interfejs z panelem wyszukiwania i tabelą wyników.

### Ekran Startowy
Animowany splash screen z logo i spinnerem ładowania.

### Motywy
Dostępne trzy motywy kolorystyczne do wyboru.

## ⚠️ Zastrzeżenie Prawne

To narzędzie jest przeznaczone **wyłącznie do legalnych badań OSINT i celów edukacyjnych**. Użytkownicy są odpowiedzialni za przestrzeganie:

- Warunków korzystania ze skanowanych stron internetowych
- Lokalnych przepisów dotyczących zbierania danych
- Wytycznych dotyczących prywatności i etyki

**Nie używaj tego narzędzia do:**
- Nękania lub stalkingu
- Nieautoryzowanego dostępu do kont
- Jakichkolwiek nielegalnych działań

## 🤝 Współpraca

Wkład w projekt jest mile widziany! Możesz przesłać Pull Request.

1. Sforkuj repozytorium
2. Utwórz branch dla swojej funkcji (`git checkout -b feature/NowaFunkcja`)
3. Zatwierdź zmiany (`git commit -m 'Dodaj nową funkcję'`)
4. Wypchnij branch (`git push origin feature/NowaFunkcja`)
5. Otwórz Pull Request

## 📝 Licencja

Ten projekt jest licencjonowany na licencji MIT — szczegóły w pliku [LICENSE](LICENSE).

## 👤 Autor

**Stanisław Kozioł**

- GitHub: [@crahdlinuxservers-maker](https://github.com/crahdlinuxservers-maker/)

## 🙏 Podziękowania

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — Nowoczesny framework UI
- [aiohttp](https://docs.aiohttp.org/) — Asynchroniczny klient HTTP
- [Pillow](https://python-pillow.org/) — Biblioteka do przetwarzania obrazów

---

<p align="center">
  <b>⭐ Daj gwiazdkę temu repozytorium jeśli jest przydatne! ⭐</b>
</p>

<p align="center">
  © 2025 Stanisław Kozioł. Wszelkie prawa zastrzeżone.
</p>


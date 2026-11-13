# CinnamonCoffee 1.1 — poprawki głosu, menu i odtwarzania

Wersja przygotowana na podstawie przesłanego kodu CinnamonCoffee. Zawiera
8 istniejących kobiecych głosów postaci `S_F_Y_HOOKER` z GTA V oraz 31 przesłanych
plików WAV. Nagrania pozostają niezmienione; nie dodano nowych głosów AI.

## Pobieranie

Gotowa paczka instalacyjna: [CinnamonCoffee-voice-fix-1.1.zip](releases/CinnamonCoffee-voice-fix-1.1.zip).
Na stronie pliku ZIP wybierz **Download raw file**, aby pobrać archiwum.

## Co poprawiono

- Menu wyboru głosu można otworzyć podczas trwającej pętli animacji. Animacja
  kontynuuje działanie z dotychczasową szybkością.
- **Partner Voice** ma bezpośrednią pozycję w menu głównym i pozostaje także
  w **Settings**. Menu pokazuje osiem głosów i numer wersji **1.1**.
- Zmiana głosu czeka na naturalny koniec bieżącej wypowiedzi. Kilka kolejnych
  wyborów zastępuje oczekujący wybór; obowiązuje ostatni.
- Interfejs odróżnia wybrany głos od głosu potwierdzonego przez silnik gry.
  Potwierdzenie następuje w następnej klatce; odrzucone przypisanie jest ponawiane.
- Nowa kwestia nie zatrzymuje poprzedniej przy wyższym tempie. Skrypt sprawdza
  rzeczywiste odtwarzanie mowy, ochronę uruchamiania i 450 ms ciągłej ciszy.
  Okres kolejnej wypowiedzi wynosi siedem sekund od potwierdzonego końca
  poprzedniej i nie zależy od prędkości animacji. Wywołania nie używają parametrów FORCE.
- Okresowe wypowiedzi nie gromadzą się w kolejce. Ważna wypowiedź, np. końcowa,
  może poczekać w jednym oczekującym żądaniu.
- Automatyczne przełączanie głosu i dodatkowe efekty czekają na zakończenie
  wypowiedzi. Sekwencja WAV nie odcina końcówki klipu wprowadzającego.
- Wszystkie WAV-y współdzielą blokadę odtwarzania aż do końca klipu. Dzięki temu
  interwał 180 ms nie zastępuje nagrania trwającego 400 ms. Priorytetowy efekt
  może poczekać, a zaległe zwykłe efekty nie tworzą kolejki.
- Pomiar menu nie rysuje go drugi raz. Podpowiedzi są w dwóch krótkich wierszach,
  z osobnym miejscem na komunikat stanu.
- Zamknięcie menu klawiszem J nie kończy animacji, również przy przytrzymaniu
  klawisza. Zakończenie wymaga jego zwolnienia i ponownego naciśnięcia.

## Instalacja

1. Zamknij grę. Wypakuj paczkę do osobnego folderu, np. na pulpicie.
2. W PowerShell uruchom instalator z wypakowanego folderu, podając prawdziwą
   lokalizację swojej gry:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-CinnamonCoffee.ps1 -GameFolder "D:\Games\Grand Theft Auto V"
   ```

   Opcja `-ExecutionPolicy Bypass` dotyczy tylko tego uruchomienia PowerShell.
   Możesz najpierw dodać `-WhatIf`, aby wyświetlić plan bez zmieniania plików.
3. Instalator przenosi stare `CinnamonCoffee*.cs`, `.vb` i `.dll`, także z podfolderów,
   do kopii zapasowej **poza** `scripts`, a następnie zostawia jeden aktualny
   `CinnamonCoffee.3.cs`. Zachowuje istniejącą konfigurację, A-Life i WAV-y.
   Kopie wewnątrz podfolderu `scripts` mogą nadal być uruchamiane przez SHVDN.
4. Wymagane są ScriptHookV i ScriptHookVDotNet v3 zgodne z Twoją wersją GTA V.
   Po uruchomieniu w nagłówku menu powinno być **CINNAMON COFFEE 1.1**.
   Jeżeli nadal widzisz stare podpowiedzi w jednym wierszu lub dwie nakładki,
   sprawdź, czy instalator wskazywał właściwy folder gry.

Instalacja ręczna: przenieś wszystkie poprzednie kopie skryptu/DLL poza `scripts`,
skopiuj aktualny `scripts/CinnamonCoffee.3.cs` i zachowaj własne cfg, A-Life oraz
istniejące WAV-y. Nie instaluj jednocześnie źródła i skompilowanego DLL.

Mostek Autoblow jest opcjonalny i nie jest potrzebny do wyboru głosu.

## Sterowanie głosem

| Sytuacja | Klawiatura | Kontroler, ustawienia domyślne |
| --- | --- | --- |
| Otwórz lub zamknij menu głosu podczas pętli animacji | F6 | LB + Y / L1 + trójkąt |
| Poprzednia / następna pozycja | NUM8 / NUM2 | góra / dół |
| Wybierz głos | NUM5 | A / krzyżyk |
| Zamknij menu i kontynuuj animację | NUM0, J lub F6 | B / kółko albo kombinacja otwierająca |

Na padzie używany jest skonfigurowany `masterControlModifier` oraz przycisk Y
(trójkąt). Własne przypisania nawigacji z pliku cfg nadal obowiązują.
Zmiana szybkości jest wstrzymana, gdy menu głosu jest otwarte, aby nawigacja
nie zmieniała jednocześnie tempa. Sama animacja nie jest pauzowana.

Poza animacją: **J → Partner Voice** lub **J → Settings → Partner Voice**. Opcja **Automatic** przywraca
automatyczny dobór głosu; **Preview selected voice** odtwarza neutralne powitanie.
Jeżeli postać aktualnie mówi, podgląd poprosi o odczekanie do końca kwestii.
Wybór zapisuje się jako `partnerVoice` i obowiązuje również kolejne partnerki.

## Weryfikacja i ograniczenia

Cały skrypt kompiluje się z C# 5, .NET Framework 4.8 oraz oficjalnym API
ScriptHookVDotNet 3.6.0. Testy logiki używają atrap funkcji GTA i sprawdzają
oczekiwanie na koniec mowy, zmianę głosu, kolejkę, reset i menu.

```sh
python3 tests/verify_partner_audio.py /ścieżka/do/dotnet
python3 tests/verify_menu_rendering.py /ścieżka/do/dotnet
python3 tests/verify_installer.py /ścieżka/do/pwsh
python3 scripts/build_release.py
```

Testy wymagają .NET 8 SDK, Pythona 3 i PowerShell do sprawdzania instalatora.
Testy renderowania przechwytują rzeczywiste wywołania rysujące z kodu;
testy audio symulują opóźniony start i chwilowo fałszywy stan mowy.
Instalator sprawdzono na tymczasowych katalogach w PowerShell 7.4.6;
używa składni zgodnej z Windows PowerShell 5.1.
Testy nie zastępują odsłuchu i sprawdzenia
sterowania w GTA V. Środowisko użyte do prac nie zawiera gry. Sam silnik,
usunięcie postaci, anulowanie interakcji lub inny mod mogą nadal przerwać mowę.
Nie zmieniono zawartości ani formatu przesłanych nagrań.

Kod i nagrania bazowe zostały dostarczone przez użytkownika. Zachowano nagłówek
i informacje o autorach znajdujące się w kodzie; nie nadano im nowej licencji.

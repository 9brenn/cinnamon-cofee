# CinnamonCoffee 1.3 — moduł taneczny Vanilla Unicorn

Wersja przygotowana na podstawie przesłanego kodu CinnamonCoffee. Zawiera
8 istniejących kobiecych głosów postaci `S_F_Y_HOOKER` z GTA V oraz 31 przesłanych
plików WAV. Nagrania pozostają niezmienione; nie dodano nowych głosów AI.

## Pobieranie

Gotowa paczka instalacyjna: [CinnamonCoffee-club-dance-1.3.zip](releases/CinnamonCoffee-club-dance-1.3.zip).
Na stronie pliku ZIP wybierz **Download raw file**, aby pobrać archiwum.

## Nowość 1.3: Vanilla Unicorn

Dodano osobny moduł występów tanecznych, bez przebudowy dotychczasowych usług
i odtwarzania audio. W lokalu naciśnij **F7** albo wybierz
**J → Vanilla Unicorn**. Menu działa również z dotychczasową nawigacją pada.

- **Partner: perform on free stage pole** — partnerka obecna w klubie rozpoczyna
  występ na pierwszej wolnej rurze spośród trzech scenicznych stanowisk.
- **MP Female: start dance shift** — graczka o modelu `mp_f_freemode_01` rozpoczyna
  zmianę taneczną. Co 30 sekund może otrzymać napiwek $10–50, jeśli faktycznie
  tańczy i w odległości do 10 metrów są żywi męscy widzowie w tym samym klubie.
  Nie powstają nowi NPC, a obecnym widzom nie są zmieniane zadania.
  Napiwki są ewidencjonowane w `CinnamonCoffeeClub.ini` i widoczne w menu jako
  zarobek zmiany oraz łączny wynik. To osobny rejestr klubowy: API pieniędzy SHVDN
  nie obsługuje postaci MP Female, więc moduł nie udaje dopłaty do portfela GTA.
- **Dance variant** wybiera jeden z trzech istniejących tańców GTA V przed startem.
- **End show / return from stage** kończy występ i przywraca pozycję sprzed
  występu. **J** także kończy występ. **F7** zamyka lub otwiera samo menu.

Start jawnie ustawia wybraną postać na wolnym stanowisku sceny, dopasowanym do
sceny zsynchronizowanej animacji. Nie zmienia modelu ani ubrań. Zajęte rury
blokują start; moduł nie usuwa i nie przesuwa tancerek gry. W danej chwili działa
jeden występ: partnerki albo graczki. Zakres dodatku to taniec i napiwki;
nie dodano nowych scen seksualnych ani obsługi seksualnej klientów.

Podczas występu stare podążanie i automatyczne podejścia są wstrzymane, aby nie
nadpisywały tańca. Zwykłe zatrzymanie przywraca wcześniejsze flagi postaci.
Opuszczenie klubu, śmierć lub zniknięcie postaci kończy moduł bez przenoszenia
postaci z powrotem do lokalu. Wyładowanie całego skryptu zachowuje dotychczasowe
sprzątanie moda: odblokowuje gracza i zwalnia przejętą partnerkę.
Animacje mają limit pięciu sekund na załadowanie. Jeśli gra przerwie taniec,
moduł kończy występ zamiast bez końca przejmować zadania postaci.

## Zachowane funkcje głosu i odtwarzania

- Menu wyboru głosu można otworzyć podczas trwającej pętli animacji. Animacja
  kontynuuje działanie z dotychczasową szybkością.
- **Partner Voice** ma bezpośrednią pozycję w menu głównym i pozostaje także
  w **Settings**. Menu pokazuje osiem głosów i numer wersji **1.3**.
- Zmiana głosu czeka na naturalny koniec bieżącej wypowiedzi. Kilka kolejnych
  wyborów zastępuje oczekujący wybór; obowiązuje ostatni.
- Wybrany bank jest przekazywany bezpośrednio przy rozpoczynaniu każdej kwestii.
  Odczyt hasha ambientowego głosu jest wyłącznie diagnostyczny: najwyżej trzy
  próby i brak blokowania dialogów, nawet gdy silnik nie potwierdzi zmiany.
- Nowa kwestia nie zatrzymuje poprzedniej przy wyższym tempie. Skrypt sprawdza
  rzeczywiste odtwarzanie mowy, ochronę uruchamiania i 450 ms ciągłej ciszy.
  Następna kwestia otrzymuje jedną losową przerwę **2–5 sekund**, liczoną od końca
  poprzedniej. Prędkość animacji nie skraca nagrania. Wywołania nie używają FORCE.
- Skrypt odróżnia żądanie mowy od potwierdzonego rozpoczęcia. Odrzucone żądanie
  dostaje krótką próbę ponowienia; nie jest uznawane za ukończoną wypowiedź.
  Przywrócono flagę audio Director Mode na czas interakcji, aby unikać dodatkowych
  ograniczeń częstotliwości ambientowych dialogów GTA; reset przywraca flagę.
- Usunięto 1-procentową szansę mowy przy niskiej reputacji A-Life. Włączone dialogi
  pozostają regularne; pozostałe mechanizmy reputacji nie są zmieniane.
- Okresowe wypowiedzi nie gromadzą się w kolejce. Ważna wypowiedź, np. końcowa,
  może poczekać w jednym oczekującym żądaniu.
- Mowa GTA i WAV-y nie blokują się wzajemnie. Zastąpiono globalny kanał
  `SoundPlayer` niezależnymi strumieniami Windows `waveOut` dla pełnych klipów.
  Odstępy uruchamiania efektów dostosowują się do prędkości animacji: np. klipy
  400 ms mogą zaczynać się co 180 ms, nakładając się bez ucinania końcówek.
  Zachowano naturalne brzmienie i czas trwania nagrań; pliki nie są przyspieszane
  przez zmianę tonacji ani modyfikowane na dysku.
- Sekwencja efektów na kanale BJ czeka tylko na własny klip, nie na głos postaci
  ani efekty innych typów. Jednocześnie może grać do ośmiu pełnych WAV-ów.
- Pomiar menu nie rysuje go drugi raz. Podpowiedzi są w dwóch krótkich wierszach,
  z osobnym miejscem na komunikat stanu.
- **J otwiera lub zamyka menu zakończenia**, bez zmiany zadań ani playheadów
  żadnej postaci. Właściwe zakończenie zaczyna się dopiero po wyborze opcji.
  Dotyczy to również pocałunków i facesitting. Podczas intro/outro J jest
  ignorowane; przytrzymanie i powtarzanie klawisza nie anuluje aktorów.

## Instalacja

1. Zamknij grę. Wypakuj paczkę do osobnego folderu, np. na pulpicie.
2. W PowerShell uruchom instalator z wypakowanego folderu, podając prawdziwą
   lokalizację swojej gry:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-CinnamonCoffee.ps1 -GameFolder "D:\Steam\steamapps\common\Grand Theft Auto V"
   ```

   Opcja `-ExecutionPolicy Bypass` dotyczy tylko tego uruchomienia PowerShell.
   Możesz najpierw dodać `-WhatIf`, aby wyświetlić plan bez zmieniania plików.
3. Instalator przenosi stare `CinnamonCoffee*.cs`, `.vb` i `.dll`, także z podfolderów,
   do kopii zapasowej **poza** `scripts`, a następnie zostawia jeden aktualny
   `CinnamonCoffee.3.cs`. Zachowuje istniejącą konfigurację, A-Life i WAV-y.
   Kopie wewnątrz podfolderu `scripts` mogą nadal być uruchamiane przez SHVDN.
4. Wymagane są ScriptHookV i ScriptHookVDotNet v3 zgodne z Twoją wersją GTA V.
   Po uruchomieniu w nagłówku menu powinno być **CINNAMON COFFEE 1.3**.
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
| Otwórz/zamknij menu zakończenia bez przerywania pętli | J | dotychczasowa kombinacja przycisku głównego |

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
python3 tests/verify_wave_engine.py /ścieżka/do/dotnet
python3 tests/verify_finish_flow.py
python3 tests/verify_club_dance.py /ścieżka/do/dotnet
python3 tests/verify_installer.py /ścieżka/do/pwsh
python3 scripts/build_release.py
```

Testy wymagają .NET 8 SDK, Pythona 3 i PowerShell do sprawdzania instalatora.
Testy renderowania przechwytują rzeczywiste wywołania rysujące z kodu;
testy audio symulują opóźniony i odrzucony start, stały błędny hash głosu,
krótkie przerwy w sygnale i losowanie odstępu raz po faktycznym końcu kwestii.
Testy `waveOut` sprawdzają parser PCM, nakładanie pełnych klipów oraz czas życia
buforów i sprzątanie urządzeń za pomocą symulowanego sterownika.
Instalator sprawdzono na tymczasowych katalogach w PowerShell 7.4.6;
używa składni zgodnej z Windows PowerShell 5.1.
Testy nie zastępują odsłuchu ani sprawdzenia animacji scenicznych i sterowania
w GTA V. Środowisko użyte do prac nie zawiera gry. Sam silnik,
usunięcie postaci, anulowanie interakcji lub inny mod mogą nadal przerwać mowę.
Nie zmieniono zawartości ani formatu przesłanych nagrań. Nie uruchomiono tutaj
rzeczywistego sterownika dźwięku Windows. Jeśli urządzenie odrzuci format audio
albo silnik wielokrotnie nie rozpocznie żądanej kwestii, szczegóły są zapisywane
w `scripts/CinnamonCoffeeAudio.log`.

Kod i nagrania bazowe zostały dostarczone przez użytkownika. Zachowano nagłówek
i informacje o autorach znajdujące się w kodzie; nie nadano im nowej licencji.

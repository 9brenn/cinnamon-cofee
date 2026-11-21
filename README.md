# CinnamonCoffee 1.5 — czytelne menu i poprawione odstępy dialogów

Wersja przygotowana na podstawie przesłanego kodu CinnamonCoffee. Zawiera
8 istniejących kobiecych głosów postaci `S_F_Y_HOOKER` z GTA V oraz 31 przesłanych
plików WAV. Nagrania pozostają niezmienione; nie dodano nowych głosów AI.

## Pobieranie

Gotowa paczka instalacyjna: [CinnamonCoffee-voice-fix-1.5.zip](releases/CinnamonCoffee-voice-fix-1.5.zip).
Na stronie pliku ZIP wybierz **Download raw file**, aby pobrać archiwum.

## Zmiany w 1.5

- Wysokość wierszy menu i stopki uwzględnia rzeczywiste zawijanie tekstu przez
  GTA, zamiast stałej wysokości i szacowania liczby znaków. Menu jest rysowane
  najwyżej raz na klatkę, a otwarty panel ukrywa dolne podpowiedzi animacji.
- Zaktualizowane kopie CinnamonCoffee współdzielą blokadę jednego uruchomienia
  w procesie gry. Druga taka kopia nie uruchamia menu, odtwarzania ani sprzątania
  zadań aktywnej kopii. Starsze wersje bez tej ochrony trzeba usunąć instalatorem.
- Instalator rozpoznaje również kopie źródła C# ze zmienioną nazwą. Zachowuje
  je w kopii zapasowej poza `scripts`; nie usuwa dowolnych, nierozpoznanych DLL.
- Przytrzymanie J daje jedno otwarcie lub zamknięcie menu do następnego
  zwolnienia i naciśnięcia klawisza.
- Przerwa jest liczona od wykrytego końca poprzedniej wypowiedzi. Stałe ustawienia
  nie dostają losowania 2–5 sekund ani obowiązkowego minimum 450 ms.
  Przykładowo `0,5` ustawia termin kolejnej próby na koniec plus 500 ms.

Odtwarzanie pozostaje zależne od silnika GTA. Termin żądania jest sprawdzany
co klatkę; zaakceptowanie żądania i rzeczywisty początek dźwięku mogą nastąpić
później. Okresowe kwestie używają `SPEECH_PARAMS_FORCE_NORMAL` po sprawdzeniu
końca mowy, aby ograniczyć dodatkowe decyzje silnika o pominięciu dialogu.
Pozostałe kwestie zachowują dotychczasowy parametr. Skrypt nie nakłada
kolejnej kwestii na aktywną ani nie przycina nagrań,
aby sztucznie osiągnąć zadany czas. Opóźnienia i odrzucone żądania można
sprawdzić w `scripts/CinnamonCoffeeAudio.log`.

Brak numeru wersji w nagłówku oznacza, że widoczne menu nie pochodzi z tej paczki.
Po prawidłowej instalacji powinno być **CINNAMON COFFEE 1.5**. Zobacz instalację
poniżej, szczególnie gdy stare menu nadal się nakłada.

## Zachowane zmiany z 1.4

### J podczas animacji ulicznych

Otwarcie menu **Finish** nie zatwierdza zakończenia. Wybór wymaga świeżego
naciśnięcia po zwolnieniu przycisku; przytrzymany NUM5 nie może sam wybrać
pierwszej pozycji. Na ulicy podczas pętli blokowane są działania rozgrywki,
które mogą przerwać zadanie gracza. Kamera i pauza pozostają dostępne.

Podczas otwartego menu skrypt pilnuje obu klipów. Jeśli jeden zostanie przerwany,
przywraca tylko ten klip z jego własnej ostatniej poprawnej fazy. Zachowuje
oddzielne czasy obu postaci, również przy różnych prędkościach. Nie restartuje
sprawnej pary. Ochrona kończy się po wyborze zakończenia; nie działa dla martwych,
zastąpionych ani oddalonych aktorów. Otwieranie menu i przywrócenia są zapisywane
w `scripts/CinnamonCoffeeInput.log`, aby ułatwić diagnozę zachowania w grze.

### Ustawiana przerwa między kwestiami

Otwórz **J → Partner Voice** albo **F6** podczas animacji i wybierz
**Speech gap** pod listą głosów. Wpisz liczbę sekund:

- `0`: bez dodatkowego oczekiwania po wykryciu końca kwestii;
- `1`, `2`, `3`, `10` itd.: stała przerwa;
- `0.5` albo `0,5`: pół sekundy;
- `-1` lub `random`: losowanie 2–5 sekund.

Opcja **Use random 2-5 second gap** przywraca losowanie bez wpisywania tekstu.
Wartość zapisuje się w `scripts/CinnamonCoffee.cfg`, np.:

```ini
partnerSpeechGapSeconds=0
```

Zmiana podczas odtwarzania nie przerywa bieżącej kwestii. Przy wpisywaniu
animacje nadal są obsługiwane, a J i nawigacja nie sterują równocześnie menu.
Anulowanie zachowuje poprzednią wartość. Obsługiwany zakres to 0–2147483 sekund
lub `-1`. Długie odstępy uwzględniają przepełnienie zegara gry.

**0 sekund oznacza brak dodatkowej pauzy, nie nakładanie dialogów.** Koniec
mowy potwierdzany jest na kolejnej aktualizacji gry. Dla dodatnich stałych
przerw potwierdzanie mieści się w ustawionym czasie; nie dodaje kolejnych 450 ms.
Gra może odrzucić lub opóźnić żądanie, co jest zapisywane diagnostycznie.
Instalator zachowuje istniejącą konfigurację; nowy klucz zostanie dopisany
po zapisaniu ustawienia w menu. HazelnutCoffee i VanillaCoffee nie są integrowane
w tym wydaniu — zakres ograniczono do dwóch uzgodnionych poprawek.

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
  w **Settings**. Menu pokazuje osiem głosów i numer wersji **1.5**.
- Zmiana głosu czeka na naturalny koniec bieżącej wypowiedzi. Kilka kolejnych
  wyborów zastępuje oczekujący wybór; obowiązuje ostatni.
- Wybrany bank jest przekazywany bezpośrednio przy rozpoczynaniu każdej kwestii.
  Odczyt hasha ambientowego głosu jest wyłącznie diagnostyczny: najwyżej trzy
  próby i brak blokowania dialogów, nawet gdy silnik nie potwierdzi zmiany.
- Nowa kwestia nie zatrzymuje poprzedniej przy wyższym tempie. Skrypt sprawdza
  rzeczywiste odtwarzanie mowy i potwierdzenie jej zakończenia.
  Następna kwestia otrzymuje ustawioną przerwę, domyślnie losową **2–5 sekund**,
  liczoną od końca poprzedniej. Prędkość animacji nie skraca nagrania.
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
2. Uruchom **Install-CinnamonCoffee.cmd** z wypakowanego folderu. Domyślna
   ścieżka to `D:\Steam\steamapps\common\Grand Theft Auto V`, jeżeli zawiera grę;
   w przeciwnym razie instalator poprosi o folder. Sprawdź wyświetloną ścieżkę.
   Alternatywnie otwórz PowerShell w wypakowanym folderze i uruchom:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-CinnamonCoffee.ps1 -GameFolder "D:\Steam\steamapps\common\Grand Theft Auto V"
   ```

   Opcja `-ExecutionPolicy Bypass` dotyczy tylko tego uruchomienia PowerShell.
   Możesz najpierw dodać `-WhatIf`, aby wyświetlić plan bez zmieniania plików.
3. Instalator przenosi stare `CinnamonCoffee*.cs`, `.vb` i `.dll`, także z podfolderów,
   oraz pliki C# zawierające klasę CinnamonCoffee mimo zmienionej nazwy,
   do kopii zapasowej **poza** `scripts`, a następnie zostawia jeden aktualny
   `CinnamonCoffee.3.cs`. Zachowuje istniejącą konfigurację, A-Life i WAV-y.
   Kopie wewnątrz podfolderu `scripts` mogą nadal być uruchamiane przez SHVDN.
4. Wymagane są ScriptHookV i ScriptHookVDotNet v3 zgodne z Twoją wersją GTA V.
   Po uruchomieniu w nagłówku menu powinno być **CINNAMON COFFEE 1.5**.
   Jeżeli nadal widzisz stare podpowiedzi w jednym wierszu lub dwie nakładki,
   sprawdź, czy instalator wskazywał właściwy folder gry. Wyłącz i uruchom GTA
   ponownie; samo podmienienie pliku podczas gry nie wyładuje starej kopii.
   Nowa wersja zapisuje swój start w `scripts/CinnamonCoffeeStartup.log`.

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
python3 tests/verify_master_input.py /ścieżka/do/dotnet
python3 tests/verify_street_finish_guard.py Mod/scripts/CinnamonCoffee.3.cs /ścieżka/do/dotnet
python3 tests/verify_speech_gap.py /ścieżka/do/dotnet
python3 tests/verify_speech_pacing.py /ścieżka/do/dotnet
python3 tests/verify_single_instance.py /ścieżka/do/dotnet
python3 tests/verify_club_dance.py /ścieżka/do/dotnet
python3 tests/verify_installer.py /ścieżka/do/pwsh
python3 scripts/build_release.py
```

Testy wymagają .NET 8 SDK, Pythona 3 i PowerShell do sprawdzania instalatora.
Testy renderowania przechwytują rzeczywiste wywołania rysujące z kodu;
testy audio symulują opóźniony i odrzucony start, stały błędny hash głosu,
krótkie przerwy w sygnale i losowanie odstępu raz po faktycznym końcu kwestii.
Testy stałych przerw używają rzeczywistej metody wywołującej mowę i oddzielają
termin żądania od potwierdzonego startu. Model decyzji silnika jest symulacją;
nie dowodzi, że GTA zaakceptuje każdy parametr lub zachowa identyczną latencję.
Testy blokady uruchomienia obejmują osobno skompilowane kopie, wyścig o właściciela
i zwalnianie z innego wątku. Na Linuksie używają blokady pliku; nazwany semafor
Windows i sam launcher CMD wymagają sprawdzenia na Windows.
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

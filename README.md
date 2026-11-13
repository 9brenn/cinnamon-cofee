# CinnamonCoffee — poprawki głosu i odtwarzania

Wersja przygotowana na podstawie przesłanego kodu CinnamonCoffee. Zawiera
8 istniejących kobiecych głosów postaci `S_F_Y_HOOKER` z GTA V oraz 31 przesłanych
plików WAV. Nagrania pozostają niezmienione; nie dodano nowych głosów AI.

## Pobieranie

Gotowa paczka instalacyjna: [CinnamonCoffee-live-voices.zip](releases/CinnamonCoffee-live-voices.zip).
Na stronie pliku ZIP wybierz **Download raw file**, aby pobrać archiwum.

## Co poprawiono

- Menu wyboru głosu można otworzyć podczas trwającej pętli animacji. Animacja
  kontynuuje działanie z dotychczasową szybkością.
- Zmiana głosu czeka na naturalny koniec bieżącej wypowiedzi. Kilka kolejnych
  wyborów zastępuje oczekujący wybór; obowiązuje ostatni.
- Nowa kwestia nie zatrzymuje poprzedniej przy wyższym tempie. Skrypt sprawdza
  rzeczywiste odtwarzanie mowy oraz krótką ochronę uruchamiania, zamiast uznawać
  każdą kwestię za zakończoną po trzech sekundach.
- Okresowe wypowiedzi nie gromadzą się w kolejce. Ważna wypowiedź, np. końcowa,
  może poczekać w jednym oczekującym żądaniu.
- Automatyczne przełączanie głosu i dodatkowe efekty czekają na zakończenie
  wypowiedzi. Sekwencja WAV nie odcina końcówki klipu wprowadzającego.
- Zamknięcie menu klawiszem J nie kończy animacji, również przy przytrzymaniu
  klawisza. Zakończenie wymaga jego zwolnienia i ponownego naciśnięcia.

## Instalacja

1. Zamknij grę i zachowaj kopię dotychczasowych plików moda.
2. Zainstaluj ScriptHookV oraz ScriptHookVDotNet v3 zgodne z Twoją wersją GTA V.
3. Przenieś stary `scripts/CinnamonCoffee.cs` oraz ewentualny `CinnamonCoffee.dll`
   poza folder `scripts`. Pozostaw tylko jedną wersję skryptu.
4. Wypakuj folder `scripts` z paczki do głównego folderu GTA V.
   Nazwa `CinnamonCoffee.3.cs` wybiera API v3.
5. Jeśli masz własne ustawienia, zachowaj istniejący `CinnamonCoffee.cfg`.
   Nie usuwaj zapisu `CinnamonCoffeeALife.ini`. Paczka nie zawiera pliku A-Life.

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

Poza animacją: **J → Settings → Partner Voice**. Opcja **Automatic** przywraca
automatyczny dobór głosu; **Preview selected voice** odtwarza neutralne powitanie.
Jeżeli postać aktualnie mówi, podgląd poprosi o odczekanie do końca kwestii.
Wybór zapisuje się jako `partnerVoice` i obowiązuje również kolejne partnerki.

## Weryfikacja i ograniczenia

Cały skrypt kompiluje się z C# 5, .NET Framework 4.8 oraz oficjalnym API
ScriptHookVDotNet 3.6.0. Testy logiki używają atrap funkcji GTA i sprawdzają
oczekiwanie na koniec mowy, zmianę głosu, kolejkę, reset i menu.

```sh
python3 tests/verify_partner_audio.py /ścieżka/do/dotnet
python3 scripts/build_release.py
```

Testy wymagają .NET 8 SDK i Pythona 3. Nie zastępują odsłuchu i sprawdzenia
sterowania w GTA V. Środowisko użyte do prac nie zawiera gry. Sam silnik,
usunięcie postaci, anulowanie interakcji lub inny mod mogą nadal przerwać mowę.
Nie zmieniono zawartości ani formatu przesłanych nagrań.

Kod i nagrania bazowe zostały dostarczone przez użytkownika. Zachowano nagłówek
i informacje o autorach znajdujące się w kodzie; nie nadano im nowej licencji.

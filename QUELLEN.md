# Quellen

Wo der Radar von selbst sucht und wo du noch suchen kannst. Die Liste ist ein Startpunkt, keine Empfehlung einzelner Anbieter (Stand Oktober 2026).

## Was der Radar von selbst durchsucht

| Quelle | Wie | Einstellung |
|---|---|---|
| LinkedIn | über die offene Bibliothek [JobSpy](https://github.com/speedyapply/JobSpy) | läuft immer |
| Indeed | über JobSpy | läuft immer. Antwortet Indeed in deinem Netz nicht: `JOBSPY_SITES=linkedin` in `.env` |
| das offene Web | über die [Firecrawl](https://www.firecrawl.dev)-Websuche: Plattformen, Ausschreibungen auf Firmenseiten, Verbände, Verzeichnisse | braucht einen Firecrawl-Schlüssel |

JobSpy kann außerdem Glassdoor, Google Jobs, ZipRecruiter (USA, Kanada), Bayt (Golfstaaten), Naukri (Indien) und BDJobs (Bangladesch). Einschalten über `JOBSPY_SITES` in `.env`, zum Beispiel `JOBSPY_SITES=linkedin,indeed,glassdoor`, oder für einen einzelnen Suchbegriff mit `"sites": ["glassdoor"]`.

**Tipp:** Jede Seite aus der Liste unten kann der Radar gezielt durchsuchen. Dafür in `search_terms.firecrawl_search` eine Suche mit `site:` anlegen, zum Beispiel `site:freelancermap.de Projektmanagement remote`.

## Die sieben Arten von Chancen

So sortiert der Radar seine Funde. Jede Suche bekommt eine dieser Kategorien.

| Kategorie | Was dahinter steckt | Beispiel-Suche |
|---|---|---|
| `ausschreibung` | konkrete Stellen- und Projektanzeigen | „Projektleitung Marketing Teilzeit remote" |
| `plattform` | Plattformen und Firmen, die laufend Leute wie dich vermitteln oder buchen | „Plattform sucht freie Trainer jetzt bewerben" |
| `kooperation` | Agenturen, Programme und Selbstständige, denen deine Fähigkeit fehlt | „Kooperationspartner gesucht Personalentwicklung" |
| `lehre` | Kurse, Weiterbildungen, Hochschulen, Volkshochschulen, Fernschulen | „Dozent gesucht Buchhaltung freiberuflich online" |
| `netzwerk` | Berufsverbände, Alumni-Gruppen, Kammern, Communities deiner Ausbildung | „Berufsverband Logistik Stellenbörse" |
| `sichtbarkeit` | Verzeichnisse und Profile, über die man dich findet | „Experten-Verzeichnis Datenschutz eintragen" |
| `nische` | ungewöhnliche Wege, etwa über Sprachen, Länder oder seltene Kombinationen | „German-speaking customer success remote" |

## Weitere Quellen zum Selbst-Prüfen

| Bereich | Seiten |
|---|---|
| Jobbörsen Deutschland | [Jobsuche der Bundesagentur für Arbeit](https://www.arbeitsagentur.de/jobsuche/), [StepStone](https://www.stepstone.de), [XING Jobs](https://www.xing.com/jobs), [Glassdoor](https://www.glassdoor.de) |
| Österreich und Schweiz | [AMS](https://www.ams.at), [karriere.at](https://www.karriere.at), [jobs.ch](https://www.jobs.ch), [jobup.ch](https://www.jobup.ch) |
| öffentlicher Dienst | [service.bund.de](https://www.service.bund.de), [Interamt](https://www.interamt.de) |
| Wissenschaft und Bildung | [academics.de](https://www.academics.de), [Volkshochschulen](https://www.volkshochschule.de) |
| freie Projekte | [freelancermap](https://www.freelancermap.de), [GULP](https://www.gulp.de), [Malt](https://www.malt.de), [Upwork](https://www.upwork.com) |
| remote arbeiten | [We Work Remotely](https://weworkremotely.com), [Remote OK](https://remoteok.com), [Remotive](https://remotive.com) |
| Jobs mit Sinn | [GoodJobs](https://www.goodjobs.eu) |
| Netzwerke | dein Berufsverband, Alumni-Gruppe deiner Hochschule, IHK oder Handwerkskammer, LinkedIn-Gruppen deiner Branche |

# Term Frequency in German Bundestag Debates

Counts how often given words appear in speeches in the German federal
parliament, broken down by parliamentary group (*Fraktion*). Any term can be
searched; the worked example below uses **"Regenbogenflagge"** and
**"Regenbogenfahne"** (German for *rainbow flag*).

Data source: the Bundestag's open-data service
(<https://www.bundestag.de/services/opendata>), which publishes every plenary
session as an XML transcript. Covered are the 19th to 21st electoral terms —
561 transcripts, 68,660 speeches, October 2017 to November 2026.

## Files

```
download_plenarprotokolle.R  downloads the transcripts into Plenarprotokolle/
begriffsanalyse.py           searches them, writes begriffsanalyse.csv
begriffsanalyse.csv          the matches found, each with its context
```

Requires R 3.2 or newer (tested with 4.3.1) and Python 3.6 or newer (tested with
3.14). Neither script needs a package beyond what ships with the language, and
neither contains an absolute path. Both files are UTF-8 without a BOM.

## Usage

Set the working directory to the project folder, then run:

```r
setwd("path/to/project")
source("download_plenarprotokolle.R")
```

Creates `Plenarprotokolle/` and fetches every transcript not already there, so
re-running it just picks up new sessions. Takes about an hour on a full run.

```bash
python3 begriffsanalyse.py
```

Prints a summary table and writes `begriffsanalyse.csv`. Takes about a minute
and needs no network access.

To search for other terms, pass them as arguments instead of editing the file:

```bash
python3 begriffsanalyse.py Klimageld Lieferketten-gesetz --csv klimageld.csv
```

A hyphen inside a term marks an optional break: `Lieferketten-gesetz` matches
*Lieferkettengesetz*, *Lieferketten-Gesetz* and *Lieferketten Gesetz* alike,
including a break across a line end. Without arguments the script uses the terms
in its `BEGRIFFE` list.

**Multi-word terms must be quoted**, or the shell passes them as separate terms
and the search becomes an OR over single words:

```bash
python3 begriffsanalyse.py "soziale Marktwirtschaft"   # one phrase
python3 begriffsanalyse.py soziale Marktwirtschaft     # two terms — different!
```

In a quoted phrase, inflection applies to every word, so
`"geschlechtergerechte Sprache"` also finds *geschlechtergerechter Sprache* and
*geschlechtergerechten Sprache*. Any amount of whitespace, including a line
break, is allowed between the words — transcripts contain both.

## How it works

The analysis reads each `<rede>` (speech) element, takes the speaker's
parliamentary group from it, and counts only the speaker's own words — applause
and heckling live in separate elements and are skipped, as are interruptions by
the chair. Group spellings vary in the source data ("DIE LINKE", "Die Linke")
and are normalised to one label each.

The search pattern is built from the list of terms, and always also matches
plurals, inflections and compounds that begin with the term:
*Regenbogenflagge* finds *Regenbogenflaggen* and *Regenbogenflaggenverbot* too,
but not *Riesenregenbogenflagge*. Case never matters. What
it does not match is a different word that merely starts the same way, such as
*Regenbogenfamilie*, because the whole term has to occur. Every run prints the
pattern it used and the word forms it actually found — worth reading, since that
list is what exposes unintended matches.

Since larger groups give more speeches, the headline figure is the **share of a
group's speeches containing a match**, per thousand (‰).

## Results for the rainbow-flag example

Searching *Regenbogenflagge* and *Regenbogenfahne* across all 561 transcripts
yields 102 mentions in 75 speeches:

| Parliamentary group | Speeches | With a match | Share ‰ |
|---|---:|---:|---:|
| **AfD** | 9,610 | **34** | **3.5** |
| Independent MPs (*fraktionslos*) | 775 | 2 | 2.6 |
| Grüne (Greens) | 8,734 | 14 | 1.6 |
| Die Linke (The Left) | 6,368 | 5 | 0.8 |
| SPD | 12,051 | 8 | 0.7 |
| CDU/CSU | 15,666 | 9 | 0.6 |
| FDP | 6,208 | 2 | 0.3 |
| Federal government (cabinet) | 8,016 | 1 | 0.1 |
| BSW | 159 | 0 | 0.0 |

Speakers holding government office are listed in the transcripts without a
parliamentary group, so they are counted separately rather than credited to their
party. The script splits them by office: cabinet members (above), junior
ministers and government commissioners (950 speeches), state representatives in
the Bundesrat (94) and a few other office-holders such as the parliamentary
commissioner for the armed forces (29) — none of the latter three produced a
match. Both *fraktionslos* matches are by the same independent MP, and the single
cabinet match is Chancellor Friedrich Merz in July 2025. Neither of those two
rows carries enough cases to compare against the parliamentary groups.

Sorting this out needs a little care, because the transcripts are not perfectly
consistent: state ministers from Bavaria, Saxony and Hesse carry the title
*Staatsminister*, the same word federal junior ministers use, and are told apart
by the state named in brackets; one state premier is listed with his *Land* in
the party field instead of a role; one commissioner's office appears only in the
running text; and two roles have a typo that splits off the first letter
("B undesministerin"). The script handles all four cases, so no speech is left
in an unrecognised category.

Among the parliamentary groups, the AfD mentions the rainbow flag about twice as
often, relative to its number of speeches, as the next one. 70 of the 102
mentions fall in the 21st term, driven by the dispute over flying the flag on the
Reichstag building during Christopher Street Day.

**Two caveats.** A mention is not a position — the script shows who raises the
subject, not whether they are for or against it. And several groups have fewer
than ten matching speeches, so their shares are not precise.

## Credits

Both scripts, and this README, were written by **Claude Code (Opus 5)**,
Anthropic's agentic coding tool. The analysis questions and the choice of search
terms were the repository owner's.

The transcripts are official publications of the German Bundestag; re-use is
governed by the Bundestag's own terms.

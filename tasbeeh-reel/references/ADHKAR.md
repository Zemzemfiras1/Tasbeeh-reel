# Dhikr library: the seven recommended adhkar

Supplied by the user. Wording is fixed: do not change it. Use with `--dhikr <number or name>` in `scripts/render.py` (the same text lives in `ADHKAR` in that file). Default count for every reel is 33.

| # | Name keyword | Arabic | Transliteration | Meaning |
|---|---|---|---|---|
| 1 | `subhanallah` | سُبْحَانَ اللَّهِ | SubhanAllah | Glory be to Allah. |
| 2 | `alhamdulillah` | الْحَمْدُ لِلَّهِ | Alhamdulillah | All praise and thanks belong to Allah. |
| 3 | `akbar` | اللَّهُ أَكْبَرُ | Allahu Akbar | Allah is the Greatest. |
| 4 | `tahlil` | لَا إِلَٰهَ إِلَّا اللَّهُ | La ilaha illa Allah | There is no god worthy of worship except Allah. |
| 5 | `istighfar` | أَسْتَغْفِرُ اللَّهَ | Astaghfirullah | I seek forgiveness from Allah. |
| 6 | `bihamdihi` | سُبْحَانَ اللَّهِ وَبِحَمْدِهِ | SubhanAllahi wa bihamdihi | Glory be to Allah and praise be to Him. |
| 7 | `hawqala` | لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ | La hawla wa la quwwata illa billah | There is no power and no strength except through Allah. |

Closing line from the user's list, usable as caption text on request: "May Allah keep your tongue busy with His remembrance and your heart connected to Him. Ameen."

Examples:

```bash
python scripts/render.py --dhikr 1
python scripts/render.py --dhikr 7 --count-interval 1.4 --scene rain-flower
```

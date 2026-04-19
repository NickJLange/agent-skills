# Output Format Examples

## Luna Digest (default)

```
[Video Title] transcript (what matters):
    •    A CuTe layout = (shape, stride). It maps logical tensor coordinates to memory offsets.
    •    Layouts can be nested tuples, not just flat 2D (M,N). That's how interleaved/complex tilings are represented.
    •    Two key viewpoints:
    ◦    Coordinate function: takes structured coordinates (nested tuples) → offset
    ◦    Layout function: takes linear index → offset (via colexicographic unflatten/refinement)
    •    Important distinction in nested tuples:
    ◦    rank = number of top-level modes
    ◦    length = number of leaf entries
    ◦    size = product of entries
    •    Core operations discussed:
    ◦    Composition (A ∘ B): layout-level composition that represents function composition when possible.
    ◦    Complementation
    ◦    Logical divide / logical product (built from composition + complement + concat)
    •    Big insight: even if inputs look simple (e.g., row-major), composition can produce nontrivial interleaved nested layouts naturally.
            
    •    Caveat raised in discussion:
    ◦    "Layout composition" is stricter than plain functional composition; it may not always exist in the desired closed algebraic sense.
        If you want, next I can make a 1-page cheat sheet with concrete examples.
```

## Chapters

```
00:00 Introduction
02:15 Background and motivation
05:30 Main approach
12:45 Results and evaluation
18:20 Limitations and future work
21:00 Q&A
```

## Summary

A 5-10 sentence overview covering the video's main points, key arguments, and conclusions. Written in third person, present tense.

## Chapter Summaries

```
## 00:00 Introduction (2 min)
The speaker introduces the topic of X and explains why it matters for Y.

## 02:15 Background (3 min)
A review of prior work in the field, covering approaches A, B, and C.
```

## Thread (Twitter/X)

```
1/ Just watched an incredible talk on [topic]. Here are the key takeaways: 🧵

2/ First insight: [point]. This matters because [reason].

3/ The surprising part: [unexpected finding]. Most people assume [common belief], but the data shows otherwise.

4/ Practical takeaway: [actionable advice].

5/ Full video: [URL]
```

## Blog Post

Full article with:
- Title
- Introduction paragraph
- H2 sections for each major topic
- Key quotes (with timestamps)
- Conclusion / takeaways

## Quotes

```
"The most important thing is not the model size, but the data quality." — 05:32
"We found that scaling past 70B parameters gave diminishing returns." — 12:18
```

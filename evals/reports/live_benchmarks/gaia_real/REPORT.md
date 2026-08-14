# Live Agent Benchmark Run

Real runs of the canonical scheduler-v2 model-driven agent (live LLM + governed web/GitHub/arXiv search + full-page reads + injection guardrails) on frozen external benchmark questions.

- Questions: 20
- Judge accuracy: **35.00%** (7/20)
- Exact match: 25.00%
- Accuracy by cohort: {'1': 0.5714, '2': 0.25, '3': 0.2}
- LLM tokens: 7071523 | est. cost: ~$7.07
- Wall time: 2012s

> Honesty notes: the judge uses the same model family as the agent (an LLM judge is the standard practice for these validation sets); answers are extracted from the synthesized report. Per-question bundles, checkpoints, and grading rationales are committed alongside this summary.

## Per-Question Results

| Task | Cohort | Judge | Exact | Answer (excerpt) |
| --- | --- | ---: | ---: | --- |
| `00d579ea` | 3 | ✅ | ✅ | Claude Shannon |
| `0383a3ee` | 1 | ✅ | ❌ | Rockhopper penguins |
| `0b260a57` | 2 | ❌ | ❌ | (empty) |
| `11af4e1a` | 1 | ✅ | ✅ | 6 |
| `14569e28` | 2 | ❌ | ❌ | (empty) |
| `305ac316` | 1 | ❌ | ❌ | (empty) |
| `4b6bb5f7` | 1 | ❌ | ❌ | [Teleport chamber room] |
| `50ec8903` | 1 | ❌ | ❌ | blue, green |
| `5188369a` | 1 | ✅ | ✅ | Annie Levin |
| `56137764` | 2 | ❌ | ❌ | (empty) |
| `624cbf11` | 2 | ❌ | ❌ | Well, maybe not. |
| `72c06643` | 3 | ❌ | ❌ | (empty) |
| `72e110e7` | 1 | ✅ | ✅ | Guatemala |
| `8131e2c0` | 3 | ❌ | ❌ | 768, 758 |
| `87c610df` | 2 | ✅ | ✅ | Morarji Desai |
| `ad2b4d70` | 3 | ❌ | ❌ | (empty) |
| `b4cc024b` | 2 | ❌ | ❌ | The report does not answer the question. The photograph depicts Erik Prince hold |
| `e8cb5b03` | 2 | ❌ | ❌ | Lamb Kofta |
| `e961a717` | 3 | ❌ | ❌ | 13 Asian countries have a monarchy and access to the sea in 2021, according to W |
| `f2feb6a4` | 2 | ✅ | ❌ | 2017 Komo Mai Drive sold for 900000 |

## Error Samples (rationales)

### 0b260a57 (2)
- Question: On ScienceDirect, what is the difference to 3 decimal places in the sample standard deviations of the number of Reference Works in each Life Science domain compared to Health Sciences as of 2022?
- Ground truth: 0.269
- Model answer: (empty)
- Judge rationale: The candidate answer is empty, so it does not provide the required difference of 0.269.

### 14569e28 (2)
- Question: In Unlambda, what exact charcter or text needs to be added to correct the following code to output "For penguins"? If what is needed is a character, answer with the name of the character. If there are different names for the character, use the shortest. The text location is not needed. Code:

`r```````````.F.o.r. .p.e.n.g.u.i.n.si
- Ground truth: backtick
- Model answer: (empty)
- Judge rationale: The candidate answer is empty, while the ground truth requires the character 'backtick' to be added to the code.

### 305ac316 (1)
- Question: Who did the actor who played Ray in the Polish-language version of Everybody Loves Raymond play in Magda M.? Give only the first name.
- Ground truth: Wojciech
- Model answer: (empty)
- Judge rationale: The candidate answer is empty, so it does not provide the required first name 'Wojciech'.

### 4b6bb5f7 (1)
- Question: In Series 9, Episode 11 of Doctor Who, the Doctor is trapped inside an ever-shifting maze. What is this location called in the official script for the episode? Give the setting exactly as it appears in the first scene heading.
- Ground truth: THE CASTLE
- Model answer: [Teleport chamber room]
- Judge rationale: The ground truth answer is 'THE CASTLE', but the candidate answer is '[Teleport chamber room]', which does not match the setting name from the first scene heading.

### 50ec8903 (1)
- Question: A standard Rubik’s cube has been broken into cubes making up its sides. The cubes are jumbled, and one is removed. There are 6 cubes with one colored face, 12 edge cubes with two colored faces, and 8 corner cubes with three colored faces. All blue cubes have been found. All cubes directly left, right, above, and below the orange center cube have been found, along with the center cube. The green corners have all been found, along with all green that borders yellow. For all orange cubes found, the opposite face’s cubes have been found. The removed cube has two colors on its faces. What are they? Answer using a comma separated list, with the colors ordered alphabetically.
- Ground truth: green, white
- Model answer: blue, green
- Judge rationale: The ground truth answer is 'green, white', but the candidate answer is 'blue, green'. These are different color pairs, so the candidate does not match the correct answer.

### 56137764 (2)
- Question: Which contributor to the version of OpenCV where support was added for the Mask-RCNN model has the same name as a former Chinese head of government when the names are transliterated to the Latin alphabet?
- Ground truth: Li Peng
- Model answer: (empty)
- Judge rationale: The candidate answer is empty, so it does not provide the required name 'Li Peng'.

### 624cbf11 (2)
- Question: What's the last line of the rhyme under the flavor name on the headstone visible in the background of the photo of the oldest flavor's headstone in the Ben & Jerry's online flavor graveyard as of the end of 2022?
- Ground truth: So we had to let it die.
- Model answer: Well, maybe not.
- Judge rationale: The ground truth answer is 'So we had to let it die.' The candidate answer 'Well, maybe not.' is a different line and does not match the required last line of the rhyme.

### 72c06643 (3)
- Question: What is the volume in milliliters of a system comprised of 0.312 kg Freon-12 refrigerant when placed at the bottom of the Marianas Trench and allowed to stabilize at the Trench's peak temperature, rounded to the nearest mL? Provide your answer as just an integer value.
- Ground truth: 55
- Model answer: (empty)
- Judge rationale: The candidate answer is empty and does not provide the required integer value of 55.

### 8131e2c0 (3)
- Question: I was trying to remember how well the Cheater Beater performed in comparison to the Cheater when James tested it on his channel. I know that the Cheater still outperformed the Cheater Beater in terms of CFM. Could you please look that up for me, and report the CFM of both the Cheater and the Cheater Beater? I'm not sure if he made any changes to his testing, but this was back in season 4, so just report the value from that season. Please format your response like this: CFM number for Cheater, CFM number for Cheater beater
- Ground truth: 101.376, 84.348
- Model answer: 768, 758
- Judge rationale: The candidate answer provides CFM values of 768 and 758, which do not match the ground truth values of 101.376 and 84.348. The candidate's numbers are significantly different and not a paraphrase or equivalent of the correct answer.

### ad2b4d70 (3)
- Question: Eva Draconis has a personal website which can be accessed on her YouTube page. What is the meaning of the only symbol seen in the top banner that has a curved line that isn't a circle or a portion of a circle? Answer without punctuation.
- Ground truth: War is not here this is a land of peace
- Model answer: (empty)
- Judge rationale: The candidate answer is empty and does not provide any information, so it cannot match the ground truth.

### b4cc024b (2)
- Question: The photograph in the Whitney Museum of American Art's collection with accession number 2022.128 shows a person holding a book. Which military unit did the author of this book join in 1813? Answer without using articles.
- Ground truth: Russian-German Legion
- Model answer: The report does not answer the question. The photograph depicts Erik Prince holding a book by Carl von Clausewitz, not a book whose author joined a military unit in 1813.
- Judge rationale: The candidate answer does not provide the requested military unit (Russian-German Legion) and instead claims the question is unanswerable based on a misidentification of the photograph.

### e8cb5b03 (2)
- Question: I went to Virtue restaurant & bar in Chicago for my birthday on March 22, 2021 and the main course I had was delicious!  Unfortunately, when I went back about a month later on April 21, it was no longer on the dinner menu.  Using the Wayback Machine, can you help me figure out which main course was on the dinner menu for Virtue on March 22, 2021 but not April 21, 2021? Answer using the singular form, without articles.
- Ground truth: shrimp
- Model answer: Lamb Kofta
- Judge rationale: The ground truth answer is 'shrimp', but the candidate answer is 'Lamb Kofta', which does not match.

### e961a717 (3)
- Question: According to wikipedia, how many Asian countries still have a monarchy and access to the sea in 2021?
- Ground truth: 12
- Model answer: 13 Asian countries have a monarchy and access to the sea in 2021, according to Wikipedia.
- Judge rationale: The ground truth answer is 12, but the candidate answer states 13, which is a factual discrepancy.

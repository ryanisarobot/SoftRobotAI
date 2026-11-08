# MVP design-questionnaire research map (2026-11-08)
This map separates existing evidence from unresolved design choices. Existing studies establish broad patterns, not universal settings for this robot. The questionnaire is a **preference elicitation** exercise; its answers cannot establish health outcomes or validate physical safety.

| Topic from shared Google Doc | Evidence that already exists | Decision still worth eliciting for this MVP | Better addressed outside survey |
|---|---|---|---|
| Conversation | Older adults often value active listening, context-aware proactivity, privacy and personalized speech [1]; adoption preferences are heterogeneous [2]. | AI personality response appropriateness, understanding and naturalness through the controlled 8-condition experiment. | Speech rate, voice, timing, interruption latency through listening tests / instrumentation rather than imagined preferences. |
| Relationship/personality | Older adults anticipate assistant/companion roles, empathetic responses and autonomy [1,2]. | Preferred role, emotion response, humor. | Long-term bond, dependency and changes in attachment: longitudinal observations. |
| Memory | Privacy control and contextual memory commonly emerge as requirements [1,3,4]. | Categories users *authorize* for storage, approval mechanism, disclosure boundaries. | Actual recall accuracy, deletion correctness, access-control security: functional tests. |
| Interaction initiation | Context of solitude vs public settings affects desired robot activity [1]; advice that impinges on autonomy may frustrate users [5]. | Conditions for initiating conversation. | Frequency optimization by actual repeated-use trials. |
| Physical affection | Older adults often favor tactile, soft robotic pets [6,7]. | Willingness to be hugged, permission before a hug, what interactions interest them. | Force, pressure, skin contact time, pinch risk, emergency release: engineering safety tests, not opinion polls. |
| Appearance/voice | Familiar animal-like soft embodiments have appeared preferable in some studies [6,7], but preferences differ in broader reviews [2]. | Cat/dog/bear/form factor preference, concern about tactile comfort. | Exact sizing, voice speed, acoustic range: real examples and usability testing. |
| Autonomy/control | Co-design raises control and surveillance risks [1,4]. | Preferred immediate stop method, memory controls and adjustments. | Safety limits and fail-safe performance: engineering tests. |
| Privacy/trust | Systematic reviews describe multidimensional privacy impacts [3]. | Information-sharing permissions and personal-memory choices. | Privacy policy, legal compliance and data security are non-negotiable design requirements. |
| Accessibility | Reviews describe variability in interaction modalities and usability needs [2,8]. | Voice/buttons/interface preference and desired user adjustments. | Speech intelligibility, volume and setup usability with actual users in realistic settings. |
| Usage context | Context-specific design and care-home implementation require site-specific requirements [9,10]. | Likely location, use scenario, feature priority. | Cleaning procedures, maintenance needs, staff workflow: field testing. |
| Long-term adoption | Robotic pets have been studied over weeks/months and acceptance is context-sensitive [5,11]. | Anticipated barrier and what might sustain use. | True retention and loneliness effects require longitudinal controlled research, not preference questions [12,13]. |

## Research and background links
1. Irfan, Kuoppamäki & Skantze (2024): https://pmc.ncbi.nlm.nih.gov/articles/PMC11163135/
2. What matters most to older adults? systematic review (2026): https://www.sciencedirect.com/science/article/pii/S0167494326000117
3. Privacy beyond Data: systematic review (2024): https://doi.org/10.1145/3689216
4. Promising directions for human-robot interactions defined by older adults (2024): https://pmc.ncbi.nlm.nih.gov/articles/PMC11077273/
5. MIT Media Lab older-adult design and month-long study: https://www.media.mit.edu/articles/designing-social-robots-for-older-adults/
6. Bradwell et al., care-home user-centered robot pet design (2021): https://pmc.ncbi.nlm.nih.gov/articles/PMC8593804/
7. Companion robots for older people, roboticist-vs-user preference (2019): https://pmc.ncbi.nlm.nih.gov/articles/PMC6773331/
8. Considerations for designing socially assistive robots for older adults (2025): https://pmc.ncbi.nlm.nih.gov/articles/PMC12571604/
9. Context-based participatory robot design (2025): https://www.sciencedirect.com/science/article/pii/S2949782525000076
10. Care-home co-design / staff usability (2025): https://aging.jmir.org/2025/1/e75288/
11. Robotic pet use among community-dwelling older adults: https://pubmed.ncbi.nlm.nih.gov/32789476/
12. 2026 systematic review of conversational agents and loneliness: https://pubmed.ncbi.nlm.nih.gov/41556104/
13. 2024 meta-analysis social robots, depression and loneliness: https://pubmed.ncbi.nlm.nih.gov/38614134/
14. Social robot adoption scoping review: https://link.springer.com/article/10.1007/s12369-023-01012-1
15. Survey instrument UNRAQ, multi-stakeholder care robot expectations: https://pmc.ncbi.nlm.nih.gov/articles/PMC8201229/
16. HHS consent guidance: https://www.hhs.gov/ohrp/regulations-and-policy/guidance/faq/informed-consent/index.html

## Scope limitations
- The questionnaire contains 21 optional items; it is not a validated psychometric instrument.
- Questions about a proposed robot measure stated preference, not reactions to an actual working robot.
- The existing controlled conversation experiment has six overall 1–7 questions and three individual-response 1–7 questions per exchange; it is kept separate.
- No changes to robot safety limits, therapy/diagnosis claims, medical functionality or long-term efficacy are justified by questionnaire responses.
- Supervisory review, approved recruitment/consent procedure and a data retention/deletion policy are required before collecting external participants.

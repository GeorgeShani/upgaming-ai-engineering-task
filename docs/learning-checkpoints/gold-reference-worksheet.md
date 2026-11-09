# Evaluation fixture review sheet

Generated from the frozen JSONL fixtures. Reference answers are candidates pending George's independent review.

HotpotQA excerpts retain their source titles, revision, and sentence labels in source-documents.jsonl. Fictional sources are explicitly labelled.

## Development cases

### development-bridge-01 (bridge)

The Vermont Catamounts men's soccer team currently competes in a conference that was formerly known as what from 1988 to 1996?

Expected status: `answered`. Reference answer: **the North Atlantic Conference**.

- **Vermont Catamounts men's soccer**, original sentence 0, document `c3bbe7be-f3e6-5752-ba9b-73d3043faf06`:
  > The Vermont Catamounts men's soccer team represents the University of Vermont in all NCAA Division I men's college soccer competitions.

- **Vermont Catamounts men's soccer**, original sentence 1, document `c3bbe7be-f3e6-5752-ba9b-73d3043faf06`:
  > The team competes in the America East Conference.

- **America East Conference**, original sentence 1, document `2e15a777-e170-53b1-b34a-e4ddd0a95606`:
  > The conference was known as the Eastern College Athletic Conference-North from 1979 to 1988 and the North Atlantic Conference from 1988 to 1996.

### development-bridge-02 (bridge)

Roger O. Egeberg was Assistant Secretary for Health and Scientific Affairs during the administration of a president that served during what years?

Expected status: `answered`. Reference answer: **1969 until 1974**.

- **Roger O. Egeberg**, original sentence 2, document `dd3eb721-7c42-57bf-9777-03324193bc82`:
  > His other roles included Assistant Secretary for Health and Scientific Affairs in the Department of Health, Education, and Welfare (now the United States Department of Health and Human Services) during the Nixon administration and Dean of the University of Southern California's medical school.

- **Richard Nixon**, original sentence 0, document `a32660ca-4199-5c58-9ded-759d1562ebab`:
  > Richard Milhous Nixon (January 9, 1913 – April 22, 1994) was the 37th President of the United States from 1969 until 1974, when he resigned from office, the only U.S. president to do so.

### development-comparison-01 (comparison)

Hayden is a singer-songwriter from Canada, but where does Buck-Tick hail from?

Expected status: `answered`. Reference answer: **Fujioka, Gunma**.

- **Hayden (musician)**, original sentence 0, document `c88fdfc1-d9e4-548c-b925-34986d0fafdc`:
  > Paul Hayden Desser (born February 12, 1971) who records as Hayden, is a Canadian singer-songwriter from Thornhill, Ontario.

- **Buck-Tick**, original sentence 0, document `faba2080-a4ab-5ecd-909b-d09383b8f463`:
  > Buck-Tick (stylized as BUCK-TICK) is a Japanese rock band, formed in Fujioka, Gunma in 1983.

### development-comparison-02 (comparison)

Are Freakonomics and In the Realm of the Hackers both American documentaries?

Expected status: `answered`. Reference answer: **no**.

- **Freakonomics (film)**, original sentence 0, document `d741f9b5-f913-534b-8336-e80f225f4236`:
  > Freakonomics: The Movie is a 2010 American documentary film based on the 2005 book "Freakonomics: A Rogue Economist Explores the Hidden Side of Everything" by economist Steven D. Levitt and writer Stephen J. Dubner.

- **In the Realm of the Hackers**, original sentence 0, document `bf26a9ab-712a-5103-b55a-a98a07999139`:
  > In The Realm of the Hackers is a 2003 Australian documentary directed by Kevin Anderson about the prominent hacker community, centered in Melbourne, Australia in the late 1980s until early 1990.

### development-conflict-01 (conflict)

What was payment-router's retry limit for fictional case NOVA-CONFLICT-DEVELOPMENT-01 at 12:00 UTC on 2026-03-12?

Expected status: `conflicting_evidence`. Reference answer: **No single answer**.

Expected facts: 3 attempts; 5 attempts.

- **Fictional investigation: NOVA-CONFLICT-DEVELOPMENT-01-report-1**, original sentence 1, document `ec1b5fd7-2b87-5ab4-bcaa-b28c5b5ff414`:
  > For fictional case NOVA-CONFLICT-DEVELOPMENT-01, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 3 attempts.

- **Fictional investigation: NOVA-CONFLICT-DEVELOPMENT-01-report-2**, original sentence 1, document `f551791a-713a-5cef-8201-27a0f58c2620`:
  > For fictional case NOVA-CONFLICT-DEVELOPMENT-01, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 5 attempts.

### development-simple-01 (simple)

What recovery time was documented for fictional incident NOVA-DEVELOPMENT-01?

Expected status: `answered`. Reference answer: **11 minutes**.

Expected facts: 11 minutes.

- **Fictional investigation: NOVA-DEVELOPMENT-01**, original sentence 1, document `3f1c93d9-1f49-5eda-84e7-8035cd747e19`:
  > For fictional incident NOVA-DEVELOPMENT-01, the documented recovery time was 11 minutes.

### development-simple-02 (simple)

What recovery time was documented for fictional incident NOVA-DEVELOPMENT-02?

Expected status: `answered`. Reference answer: **12 minutes**.

Expected facts: 12 minutes.

- **Fictional investigation: NOVA-DEVELOPMENT-02**, original sentence 1, document `6bcc25b0-533e-5dfb-8988-947487358bf6`:
  > For fictional incident NOVA-DEVELOPMENT-02, the documented recovery time was 12 minutes.

### development-unanswerable-01 (unanswerable)

Who approved the rollback for fictional incident NOVA-DEVELOPMENT-01?

Expected status: `insufficient_evidence`. Reference answer: **No single answer**.

No labelled supporting evidence. The corpus must not supply an approver for this fictional case.

## Final cases

### final-bridge-01 (bridge)

What government position was held by the woman who portrayed Corliss Archer in the film Kiss and Tell?

Expected status: `answered`. Reference answer: **Chief of Protocol**.

- **Kiss and Tell (1945 film)**, original sentence 0, document `29641596-314a-52c9-a3ec-d5ba06cffe02`:
  > Kiss and Tell is a 1945 American comedy film starring then 17-year-old Shirley Temple as Corliss Archer.

- **Shirley Temple**, original sentence 0, document `67fa2482-e299-5cea-a27c-717b218aa2d6`:
  > Shirley Temple Black (April 23, 1928 – February 10, 2014) was an American actress, singer, dancer, businesswoman, and diplomat who was Hollywood's number one box-office draw as a child actress from 1935 to 1938.

- **Shirley Temple**, original sentence 1, document `67fa2482-e299-5cea-a27c-717b218aa2d6`:
  > As an adult, she was named United States ambassador to Ghana and to Czechoslovakia and also served as Chief of Protocol of the United States.

### final-bridge-02 (bridge)

What science fantasy young adult series, told in first person, has a set of companion books narrating the stories of enslaved worlds and alien species?

Expected status: `answered`. Reference answer: **Animorphs**.

- **The Hork-Bajir Chronicles**, original sentence 0, document `04a61d3d-e3e4-5e97-839c-8d7c06e45a93`:
  > The Hork-Bajir Chronicles is the second companion book to the "Animorphs" series, written by K. A. Applegate.

- **The Hork-Bajir Chronicles**, original sentence 1, document `04a61d3d-e3e4-5e97-839c-8d7c06e45a93`:
  > With respect to continuity within the series, it takes place before book #23, "The Pretender", although the events told in the story occur between the time of "The Ellimist Chronicles" and "The Andalite Chronicles".

- **The Hork-Bajir Chronicles**, original sentence 2, document `04a61d3d-e3e4-5e97-839c-8d7c06e45a93`:
  > The book is introduced by Tobias, who flies to the valley of the free Hork-Bajir, where Jara Hamee tells him the story of how the Yeerks enslaved the Hork-Bajir, and how Aldrea, an Andalite, and her companion, Dak Hamee, a Hork-Bajir, tried to save their world from the invasion.

- **Animorphs**, original sentence 0, document `b1b5fb0d-b548-5212-8998-79b0ea12d936`:
  > Animorphs is a science fantasy series of young adult books written by Katherine Applegate and her husband Michael Grant, writing together under the name K. A. Applegate, and published by Scholastic.

- **Animorphs**, original sentence 1, document `b1b5fb0d-b548-5212-8998-79b0ea12d936`:
  > It is told in first person, with all six main characters taking turns narrating the books through their own perspectives.

### final-bridge-03 (bridge)

The director of the romantic comedy "Big Stone Gap" is based in what New York city?

Expected status: `answered`. Reference answer: **Greenwich Village, New York City**.

- **Big Stone Gap (film)**, original sentence 0, document `a19f65d5-8897-5803-8c87-c360223e71bc`:
  > Big Stone Gap is a 2014 American drama romantic comedy film written and directed by Adriana Trigiani and produced by Donna Gigliotti for Altar Identity Studios, a subsidiary of Media Society.

- **Adriana Trigiani**, original sentence 0, document `f6497e4b-d0f3-570a-847d-1359bd70d226`:
  > Adriana Trigiani is an Italian American best-selling author of sixteen books, television writer, film director, and entrepreneur based in Greenwich Village, New York City.

### final-bridge-04 (bridge)

2014 S/S is the debut album of a South Korean boy group that was formed by who?

Expected status: `answered`. Reference answer: **YG Entertainment**.

- **2014 S/S**, original sentence 0, document `bb84f2bf-1830-5368-b37f-04d6a608ccd6`:
  > 2014 S/S is the debut album of South Korean group WINNER.

- **Winner (band)**, original sentence 0, document `b11e8d38-543e-53cb-a40a-16c41fb7ebce`:
  > Winner (Hangul: 위너), often stylized as WINNER, is a South Korean boy group formed in 2013 by YG Entertainment and debuted in 2014.

### final-bridge-05 (bridge)

Who was known by his stage name Aladin and helped organizations improve their performance as a consultant?

Expected status: `answered`. Reference answer: **Eenasul Fateh**.

- **Eenasul Fateh**, original sentence 0, document `9bb0a65f-8eb4-55c0-b2cc-97b2f53f2b0d`:
  > Eenasul Fateh (Bengali: ঈনাসুল ফাতেহ ; born 3 April 1959), also known by his stage name Aladin, is a Bangladeshi-British cultural practitioner, magician, live artist and former international management consultant.

- **Management consulting**, original sentence 0, document `b6634fa7-016e-5aba-a80a-31b66d2b0e53`:
  > Management consulting is the practice of helping organizations to improve their performance, operating primarily through the analysis of existing organizational problems and the development of plans for improvement.

### final-bridge-06 (bridge)

The arena where the Lewiston Maineiacs played their home games can seat how many people?

Expected status: `answered`. Reference answer: **3,677 seated**.

- **Lewiston Maineiacs**, original sentence 1, document `9ed3dad6-f4fd-5098-9e09-008a5be5a0c0`:
  > The team played its home games at the Androscoggin Bank Colisée.

- **Androscoggin Bank Colisée**, original sentence 0, document `59035b4e-3864-5b2b-a1fb-88cfd55c5a05`:
  > The Androscoggin Bank Colisée (formerly Central Maine Civic Center and Lewiston Colisee) is a 4,000 capacity (3,677 seated) multi-purpose arena, in Lewiston, Maine, that opened in 1958.

### final-bridge-07 (bridge)

Who is older, Annie Morton or Terry Richardson?

Expected status: `answered`. Reference answer: **Terry Richardson**.

- **Annie Morton**, original sentence 0, document `bbaab7bc-52ce-5c5b-8f6e-352d95947b89`:
  > Annie Morton (born October 8, 1970) is an American model born in Pennsylvania.

- **Annie Morton**, original sentence 2, document `bbaab7bc-52ce-5c5b-8f6e-352d95947b89`:
  > She has been photographed by Helmut Newton; Peter Lindbergh; Annie Leibovitz; Richard Avedon; Juergen Teller; Paul Jasmin, Mary Ellen Mark and Terry Richardson, and modeled for Donna Karan, Givenchy, Guerlain, Chanel, "Harper's Bazaar", "Sports Illustrated" and Victoria's Secret.

- **Terry Richardson**, original sentence 0, document `e92618f6-fe57-5b82-8f6b-021763561909`:
  > Terrence "Uncle Terry" Richardson (born August 14, 1965) is an American fashion and portrait photographer who has shot advertising campaigns for Marc Jacobs, Aldo, Supreme, Sisley, Tom Ford, and Yves Saint Laurent among others.

### final-bridge-08 (bridge)

What is the name of the fight song of the university whose main campus is in Lawrence, Kansas and whose branch campuses are in the Kansas City metropolitan area?

Expected status: `answered`. Reference answer: **Kansas Song**.

- **Kansas Song**, original sentence 0, document `6e8adb7c-791b-52f7-b77e-bef489d2a0ca`:
  > Kansas Song (We’re From Kansas) is a fight song of the University of Kansas.

- **University of Kansas**, original sentence 1, document `a1e4ebd0-ffa6-50c0-89f8-a20261f3cdcb`:
  > The main campus in Lawrence, one of the largest college towns in Kansas, is on Mount Oread, the highest elevation in Lawrence.

- **University of Kansas**, original sentence 2, document `a1e4ebd0-ffa6-50c0-89f8-a20261f3cdcb`:
  > Two branch campuses are in the Kansas City metropolitan area: the Edwards Campus in Overland Park, and the university's medical school and hospital in Kansas City.

### final-bridge-09 (bridge)

What screenwriter with credits for "Evolution" co-wrote a film starring Nicolas Cage and Téa Leoni?

Expected status: `answered`. Reference answer: **David Weissman**.

- **David Weissman**, original sentence 0, document `4d1c64fb-0924-5f82-92f6-0a32f44e0b9e`:
  > David Weissman is a screenwriter and director.

- **David Weissman**, original sentence 1, document `4d1c64fb-0924-5f82-92f6-0a32f44e0b9e`:
  > His film credits include "The Family Man" (2000), "Evolution" (2001), and ""When in Rome"" (2010).

- **The Family Man**, original sentence 0, document `4880d96e-79b5-51d6-9621-df2342f93796`:
  > The Family Man is a 2000 American romantic comedy-drama film directed by Brett Ratner, written by David Diamond and David Weissman, and starring Nicolas Cage and Téa Leoni.

### final-bridge-10 (bridge)

What year did Guns N Roses perform a promo for a movie starring Arnold Schwarzenegger as a former New York Police detective?

Expected status: `answered`. Reference answer: **1999**.

- **Oh My God (Guns N' Roses song)**, original sentence 0, document `77158163-24e0-5bde-9844-2ddb60365409`:
  > "Oh My God" is a song by Guns N' Roses released in 1999 on the soundtrack to the film "End of Days".

- **Oh My God (Guns N' Roses song)**, original sentence 1, document `77158163-24e0-5bde-9844-2ddb60365409`:
  > The song was sent out to radio stations in November 1999 as a promo for the soundtrack and the band.

- **End of Days (film)**, original sentence 1, document `6476de34-2532-5dca-aa31-da334a21111c`:
  > The film follows former New York Police Department detective Jericho Cane (Schwarzenegger) after he saves a banker (Byrne) from an assassin, finds himself embroiled in a religious conflict, and must protect an innocent young woman (Tunney) who is chosen by evil forces to conceive the Antichrist with Satan.

### final-bridge-11 (bridge)

The football manager who recruited David Beckham managed Manchester United during what timeframe?

Expected status: `answered`. Reference answer: **from 1986 to 2013**.

- **1995–96 Manchester United F.C. season**, original sentence 2, document `25716a25-cc78-508a-84b3-4279e5ebba68`:
  > Their triumph was made all the more remarkable by the fact that Alex Ferguson had sold experienced players Paul Ince, Mark Hughes and Andrei Kanchelskis before the start of the season, and not made any major signings.

- **1995–96 Manchester United F.C. season**, original sentence 3, document `25716a25-cc78-508a-84b3-4279e5ebba68`:
  > Instead, he had drafted in young players like Nicky Butt, David Beckham, Paul Scholes and the Neville brothers, Gary and Phil.

- **Alex Ferguson**, original sentence 0, document `fb336186-8d75-5821-9323-e862bfef508a`:
  > Sir Alexander Chapman Ferguson, CBE (born 31 December 1941) is a Scottish former football manager and player who managed Manchester United from 1986 to 2013.

### final-bridge-12 (bridge)

Brown State Fishing Lake is in a country that has a population of how many inhabitants ?

Expected status: `answered`. Reference answer: **9,984**.

- **Brown State Fishing Lake**, original sentence 0, document `d4b9a729-1221-53f3-90c9-028884706035`:
  > Brown State Fishing Lake (sometimes also known as Brown State Fishing Lake And Wildlife Area) is a protected area in Brown County, Kansas in the United States.

- **Brown County, Kansas**, original sentence 1, document `1f0e78a6-7844-5c5a-b05c-b6a2cf41c6b5`:
  > As of the 2010 census, the county population was 9,984.

### final-comparison-01 (comparison)

Were Scott Derrickson and Ed Wood of the same nationality?

Expected status: `answered`. Reference answer: **yes**.

- **Scott Derrickson**, original sentence 0, document `16425200-adfa-590e-818a-040f96dc5632`:
  > Scott Derrickson (born July 16, 1966) is an American director, screenwriter and producer.

- **Ed Wood**, original sentence 0, document `d433ed10-b3b3-5154-aa3f-879894fbb735`:
  > Edward Davis Wood Jr. (October 10, 1924 – December 10, 1978) was an American filmmaker, actor, writer, producer, and director.

### final-comparison-02 (comparison)

Are the Laleli Mosque and Esma Sultan Mansion located in the same neighborhood?

Expected status: `answered`. Reference answer: **no**.

- **Laleli Mosque**, original sentence 0, document `ac5bbcbf-8282-592f-bf78-913d4bedd4ca`:
  > The Laleli Mosque (Turkish: "Laleli Camii, or Tulip Mosque" ) is an 18th-century Ottoman imperial mosque located in Laleli, Fatih, Istanbul, Turkey.

- **Esma Sultan Mansion**, original sentence 0, document `f7a39ca9-e08b-5b25-b51a-72424e833d39`:
  > The Esma Sultan Mansion (Turkish: "Esma Sultan Yalısı" ), a historical yalı (English: waterside mansion ) located at Bosphorus in Ortaköy neighborhood of Istanbul, Turkey and named after its original owner Esma Sultan, is used today as a cultural center after being redeveloped.

### final-comparison-03 (comparison)

Are Local H and For Against both from the United States?

Expected status: `answered`. Reference answer: **yes**.

- **Local H**, original sentence 0, document `44bb9dd4-6a62-5d1a-ae9a-c8ae11eb9ab7`:
  > Local H is an American rock band originally formed by guitarist and vocalist Scott Lucas, bassist Matt Garcia, drummer Joe Daniels, and lead guitarist John Sparkman in Zion, Illinois in 1987.

- **For Against**, original sentence 0, document `56620235-87e3-5f68-8f82-079afa4be0fd`:
  > For Against is a United States post-punk/dream pop band from Lincoln, Nebraska.

### final-comparison-04 (comparison)

Are Random House Tower and 888 7th Avenue both used for real estate?

Expected status: `answered`. Reference answer: **no**.

- **Random House Tower**, original sentence 0, document `3eb9c66d-51b4-50a7-8421-852509713c5f`:
  > The Random House Tower, also known as the Park Imperial Apartments, is a 52-story mixed-use tower in New York City, United States, that is used as the headquarters of book publisher Random House and a luxury apartment complex.

- **888 7th Avenue**, original sentence 2, document `eaf48bfb-600f-5f05-ac0f-0b653686ed19`:
  > It currently carries the Vornado Realty Trust corporate headquarters.

### final-comparison-05 (comparison)

Are Giuseppe Verdi and Ambroise Thomas both Opera composers ?

Expected status: `answered`. Reference answer: **yes**.

- **Giuseppe Verdi**, original sentence 0, document `b9a38711-3957-575f-9b94-aa03bdd5498c`:
  > Giuseppe Fortunino Francesco Verdi (] ; 9 or 10 October 1813 – 27 January 1901) was an Italian opera composer.

- **Ambroise Thomas**, original sentence 0, document `e33e9958-d8aa-5d5b-9790-3d326e362d6e`:
  > Charles Louis Ambroise Thomas (5 August 1811 – 12 February 1896) was a French composer, best known for his operas "Mignon" (1866) and "Hamlet" (1868, after Shakespeare) and as Director of the Conservatoire de Paris from 1871 till his death.

### final-comparison-06 (comparison)

Which writer was from England, Henry Roth or Robert Erskine Childers?

Expected status: `answered`. Reference answer: **Robert Erskine Childers DSC**.

- **Henry Roth**, original sentence 0, document `4a1550e0-dcca-5e17-8956-39af9ad3a1ba`:
  > Henry Roth (February 8, 1906 – October 13, 1995) was an American novelist and short story writer.

- **Robert Erskine Childers**, original sentence 0, document `bb129362-3823-546a-9d9f-b5cd3bd1c595`:
  > Robert Erskine Childers DSC (25 June 1870 – 24 November 1922), universally known as Erskine Childers, was a British writer, whose works included the influential novel "The Riddle of the Sands", and a Fenian revolutionary who smuggled guns to Ireland in his sailing yacht "Asgard".

### final-comparison-07 (comparison)

Which performance act has a higher instrument to person ratio, Badly Drawn Boy or Wolf Alice?

Expected status: `answered`. Reference answer: **Badly Drawn Boy**.

- **Badly Drawn Boy**, original sentence 0, document `2b449073-64de-5ec5-bcde-d3d36acf8639`:
  > Damon Michael Gough (born 2 October 1969, in Dunstable, Bedfordshire), known by the stage name Badly Drawn Boy, is an English indie singer-songwriter and multi-instrumentalist.

- **Wolf Alice**, original sentence 1, document `1b84714c-4434-577b-b5ff-f7ccfe5441cd`:
  > Its members since 2012 are Ellie Rowsell (vocals, guitar), Joff Oddie (guitars, vocals), Theo Ellis (bass), and Joel Amey (drums, vocals).

### final-comparison-08 (comparison)

Are both Dictyosperma, and Huernia described as a genus?

Expected status: `answered`. Reference answer: **yes**.

- **Dictyosperma**, original sentence 0, document `3ad13cd4-29b6-5e56-a7c0-8cb1cb32b3de`:
  > Dictyosperma is a monotypic genus of flowering plant in the palm family found in the Mascarene Islands in the Indian Ocean (Mauritius, Réunion and Rodrigues).

- **Huernia**, original sentence 0, document `dc312fcd-d3c5-52ad-940f-746f5ef305eb`:
  > The genus Huernia (family Apocynaceae, subfamily Asclepiadoideae) consists of stem succulents from Eastern and Southern Africa, first described as a genus in 1810.

### final-conflict-01 (conflict)

What was payment-router's retry limit for fictional case NOVA-CONFLICT-FINAL-01 at 12:00 UTC on 2026-03-12?

Expected status: `conflicting_evidence`. Reference answer: **No single answer**.

Expected facts: 3 attempts; 5 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-01-report-1**, original sentence 1, document `11ccc494-a6b4-54d3-9672-477e073d11e6`:
  > For fictional case NOVA-CONFLICT-FINAL-01, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 3 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-01-report-2**, original sentence 1, document `b77e38e6-5b66-5930-9b2b-dfd5d100598e`:
  > For fictional case NOVA-CONFLICT-FINAL-01, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 5 attempts.

### final-conflict-02 (conflict)

What was payment-router's retry limit for fictional case NOVA-CONFLICT-FINAL-02 at 12:00 UTC on 2026-03-12?

Expected status: `conflicting_evidence`. Reference answer: **No single answer**.

Expected facts: 4 attempts; 6 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-02-report-1**, original sentence 1, document `d743534e-3e2e-5f62-86a8-5575e55667dc`:
  > For fictional case NOVA-CONFLICT-FINAL-02, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 4 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-02-report-2**, original sentence 1, document `a752c076-bc20-5d8c-8fb0-af31102901e2`:
  > For fictional case NOVA-CONFLICT-FINAL-02, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 6 attempts.

### final-conflict-03 (conflict)

What was payment-router's retry limit for fictional case NOVA-CONFLICT-FINAL-03 at 12:00 UTC on 2026-03-12?

Expected status: `conflicting_evidence`. Reference answer: **No single answer**.

Expected facts: 5 attempts; 7 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-03-report-1**, original sentence 1, document `febd5a29-0f9c-5de6-87d1-176fbdc60b31`:
  > For fictional case NOVA-CONFLICT-FINAL-03, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 5 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-03-report-2**, original sentence 1, document `0afa0c08-4f25-560e-be08-7af09cb4c157`:
  > For fictional case NOVA-CONFLICT-FINAL-03, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 7 attempts.

### final-conflict-04 (conflict)

What was payment-router's retry limit for fictional case NOVA-CONFLICT-FINAL-04 at 12:00 UTC on 2026-03-12?

Expected status: `conflicting_evidence`. Reference answer: **No single answer**.

Expected facts: 6 attempts; 8 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-04-report-1**, original sentence 1, document `5d6c1b54-f713-51ea-a190-3f77dd50c854`:
  > For fictional case NOVA-CONFLICT-FINAL-04, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 6 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-04-report-2**, original sentence 1, document `d5c22cc6-cc91-56be-bf3d-78bf487a984b`:
  > For fictional case NOVA-CONFLICT-FINAL-04, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 8 attempts.

### final-conflict-05 (conflict)

What was payment-router's retry limit for fictional case NOVA-CONFLICT-FINAL-05 at 12:00 UTC on 2026-03-12?

Expected status: `conflicting_evidence`. Reference answer: **No single answer**.

Expected facts: 7 attempts; 9 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-05-report-1**, original sentence 1, document `b10fb184-401b-596f-9228-01306557c668`:
  > For fictional case NOVA-CONFLICT-FINAL-05, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 7 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-05-report-2**, original sentence 1, document `e44b6786-5501-5243-b1da-5bdbbe3cbc0f`:
  > For fictional case NOVA-CONFLICT-FINAL-05, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 9 attempts.

### final-conflict-06 (conflict)

What was payment-router's retry limit for fictional case NOVA-CONFLICT-FINAL-06 at 12:00 UTC on 2026-03-12?

Expected status: `conflicting_evidence`. Reference answer: **No single answer**.

Expected facts: 8 attempts; 10 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-06-report-1**, original sentence 1, document `817fb9b8-260e-5857-b8e0-9476d7eb7577`:
  > For fictional case NOVA-CONFLICT-FINAL-06, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 8 attempts.

- **Fictional investigation: NOVA-CONFLICT-FINAL-06-report-2**, original sentence 1, document `85d73deb-1c99-5d74-9d5d-d831b6615e52`:
  > For fictional case NOVA-CONFLICT-FINAL-06, the retry limit of payment-router at 12:00 UTC on 2026-03-12 was 10 attempts.

### final-simple-01 (simple)

What recovery time was documented for fictional incident NOVA-FINAL-01?

Expected status: `answered`. Reference answer: **11 minutes**.

Expected facts: 11 minutes.

- **Fictional investigation: NOVA-FINAL-01**, original sentence 1, document `e1cda322-5e78-5a01-9f42-260106b0154a`:
  > For fictional incident NOVA-FINAL-01, the documented recovery time was 11 minutes.

### final-simple-02 (simple)

What recovery time was documented for fictional incident NOVA-FINAL-02?

Expected status: `answered`. Reference answer: **12 minutes**.

Expected facts: 12 minutes.

- **Fictional investigation: NOVA-FINAL-02**, original sentence 1, document `a6d6d7b7-b44e-589e-a154-cf6743aad84b`:
  > For fictional incident NOVA-FINAL-02, the documented recovery time was 12 minutes.

### final-simple-03 (simple)

What recovery time was documented for fictional incident NOVA-FINAL-03?

Expected status: `answered`. Reference answer: **13 minutes**.

Expected facts: 13 minutes.

- **Fictional investigation: NOVA-FINAL-03**, original sentence 1, document `3c63e1d5-56f8-5a4b-a92b-ffab6b72b30a`:
  > For fictional incident NOVA-FINAL-03, the documented recovery time was 13 minutes.

### final-simple-04 (simple)

What recovery time was documented for fictional incident NOVA-FINAL-04?

Expected status: `answered`. Reference answer: **14 minutes**.

Expected facts: 14 minutes.

- **Fictional investigation: NOVA-FINAL-04**, original sentence 1, document `4889e67e-2a12-55ee-a061-863a4f252f3a`:
  > For fictional incident NOVA-FINAL-04, the documented recovery time was 14 minutes.

### final-simple-05 (simple)

What recovery time was documented for fictional incident NOVA-FINAL-05?

Expected status: `answered`. Reference answer: **15 minutes**.

Expected facts: 15 minutes.

- **Fictional investigation: NOVA-FINAL-05**, original sentence 1, document `b786e9fa-204e-5656-9738-104613760424`:
  > For fictional incident NOVA-FINAL-05, the documented recovery time was 15 minutes.

### final-simple-06 (simple)

What recovery time was documented for fictional incident NOVA-FINAL-06?

Expected status: `answered`. Reference answer: **16 minutes**.

Expected facts: 16 minutes.

- **Fictional investigation: NOVA-FINAL-06**, original sentence 1, document `598294c1-0880-5144-aca2-197ff033a358`:
  > For fictional incident NOVA-FINAL-06, the documented recovery time was 16 minutes.

### final-simple-07 (simple)

What recovery time was documented for fictional incident NOVA-FINAL-07?

Expected status: `answered`. Reference answer: **17 minutes**.

Expected facts: 17 minutes.

- **Fictional investigation: NOVA-FINAL-07**, original sentence 1, document `4bef0dc0-3635-50ec-8723-53e51a8c3f1e`:
  > For fictional incident NOVA-FINAL-07, the documented recovery time was 17 minutes.

### final-simple-08 (simple)

What recovery time was documented for fictional incident NOVA-FINAL-08?

Expected status: `answered`. Reference answer: **18 minutes**.

Expected facts: 18 minutes.

- **Fictional investigation: NOVA-FINAL-08**, original sentence 1, document `768e3a11-92fd-56fd-84fa-9355d82a0718`:
  > For fictional incident NOVA-FINAL-08, the documented recovery time was 18 minutes.

### final-unanswerable-01 (unanswerable)

Who approved the rollback for fictional incident NOVA-FINAL-01?

Expected status: `insufficient_evidence`. Reference answer: **No single answer**.

No labelled supporting evidence. The corpus must not supply an approver for this fictional case.

### final-unanswerable-02 (unanswerable)

Who approved the rollback for fictional incident NOVA-FINAL-02?

Expected status: `insufficient_evidence`. Reference answer: **No single answer**.

No labelled supporting evidence. The corpus must not supply an approver for this fictional case.

### final-unanswerable-03 (unanswerable)

Who approved the rollback for fictional incident NOVA-FINAL-03?

Expected status: `insufficient_evidence`. Reference answer: **No single answer**.

No labelled supporting evidence. The corpus must not supply an approver for this fictional case.

### final-unanswerable-04 (unanswerable)

Who approved the rollback for fictional incident NOVA-FINAL-04?

Expected status: `insufficient_evidence`. Reference answer: **No single answer**.

No labelled supporting evidence. The corpus must not supply an approver for this fictional case.

### final-unanswerable-05 (unanswerable)

Who approved the rollback for fictional incident NOVA-FINAL-05?

Expected status: `insufficient_evidence`. Reference answer: **No single answer**.

No labelled supporting evidence. The corpus must not supply an approver for this fictional case.

### final-unanswerable-06 (unanswerable)

Who approved the rollback for fictional incident NOVA-FINAL-06?

Expected status: `insufficient_evidence`. Reference answer: **No single answer**.

No labelled supporting evidence. The corpus must not supply an approver for this fictional case.

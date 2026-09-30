abstract Metonymy = {
  flags startcat = S ;

  cat
    S ;
    NP ;
    VP ;
    V2 ;
    V3 ;
    V ;
    PP ;
    CN ;

  fun
    Pred : NP -> VP -> S ;
    NegPred : NP -> VP -> S ;
    Compl : V2 -> NP -> VP ;
    PassCompl : V2 -> NP -> VP ;
    PassCompl0 : V2 -> VP ;
    -- Retained-object passive ("he was awarded a doctorate") -- a real
    -- WiMCor shape (evaluation/pilot-decode-wimcor's Ankara/degree
    -- example: "He attended Ankara and was awarded a PhD degree")
    -- distinct from both PassCompl (whose NP is a "by"-agent) and
    -- PassCompl0 (no further NP at all). V2 cannot represent this: a V2
    -- has exactly one argument, so passivizing it necessarily promotes
    -- that argument to subject, leaving nothing to retain as object --
    -- the retained object is inherently a ditransitive (V3) phenomenon,
    -- confirmed against the pinned gf-rgl-src's own abstract Verb.gf
    -- (Slash2V3 : V3 -> NP -> VPSlash, "give it (to her)" -- the missing
    -- slot Slash2V3 leaves open is exactly the recipient/agent that
    -- passivization then promotes to subject). See MetonymyEng.gf for
    -- the concrete Slash2V3+PassVPSlash composition.
    PassComplRetained : V3 -> NP -> VP ;
    -- Intransitive verb + a single fixed-preposition oblique adjunct
    -- ("graduated WITH a diploma", "enrolled AS a doctoral student") --
    -- a real, recurring WiMCor shape found searching for more
    -- ConjClauseObject examples (Berklee/"graduated with a diploma",
    -- Rochester/"graduated with a degree"), distinct from Compl (which
    -- needs a *direct* object, not an oblique) and from the deliberately
    -- NOT-attempted general "attach any PP to any VP" mechanism
    -- documented above PassComplRetained (which risked silently
    -- reinterpreting which constituent a PP modifies). This is narrower
    -- and safe: V (this project's closed intransitive-verb lexicon, only
    -- ever combined with one of the already-closed PP constructors
    -- above) plus PP together form ONE new fixed VP shape, the same
    -- "closed word/shape, no open-ended ambiguity" discipline already
    -- used for the 14 PP constructors and BecauseS/IfS/etc. Confirmed
    -- against the pinned gf-rgl-src's own Constructors.gf, not guessed:
    -- `mkVP : V -> VP` ("sleep") composed with the separately-existing
    -- `mkVP : VP -> Adv -> VP` ("sleep here") overload is exactly this
    -- shape -- PP's own lincat is already Adv (see MetonymyEng.gf).
    ComplOblique : V -> PP -> VP ;
    -- Locative relative clause on the metonymy target itself ("X, WHERE
    -- he was awarded a degree") -- a real WiMCor shape (a place attended/
    -- studied at, with a second, later clause attached via "where"
    -- describing an event that happened there), distinct from
    -- ModifyRelVP (whose RP is the clause's own SUBJECT, "which was
    -- awarded..." -- wrong here: "he", not the target, is awarded).
    -- "Where" itself has no RGL relative-pronoun counterpart in this
    -- pinned commit (checked: Structural.gf/ExtraEngAbs.gf only declare
    -- which_who_RP/that_RP/which_RP/who_RP, no locative one) -- built
    -- instead from "at which" (a real, grammatical alternative phrasing
    -- of "where"), composing three abstract Verb.gf/Sentence.gf/Extend.gf
    -- functions confirmed against the pinned gf-rgl-src, not guessed:
    -- `VPSlashPrep : VP -> Prep -> VPSlash` ("live in (it)") opens a
    -- prepositional gap on top of an already-COMPLETE VP (so the
    -- embedded clause's own object, e.g. "a degree", stays intact --
    -- only the locative "at ___" is left open); `SlashVP : NP -> VPSlash
    -- -> ClSlash` ("(whom) he sees") supplies the embedded clause's own
    -- subject ("he"); `PiedPipingRelSlash : RP -> ClSlash -> RCl` ("with
    -- whom John lives") fronts the gap's preposition together with the
    -- relative pronoun. See MetonymyEng.gf for the concrete composition
    -- and which modules each piece needed opening from.
    ModifyRelAtVP : NP -> NP -> VP -> NP ;
    InPP : NP -> PP ;
    AboutPP : NP -> PP ;
    WithPP : NP -> PP ;
    ForPP : NP -> PP ;
    OnPP : NP -> PP ;
    AtPP : NP -> PP ;
    FromPP : NP -> PP ;
    ByPP : NP -> PP ;
    OverPP : NP -> PP ;
    UnderPP : NP -> PP ;
    DuringPP : NP -> PP ;
    NearPP : NP -> PP ;
    OfPP : NP -> PP ;
    AsPP : NP -> PP ;
    AndS : S -> S -> S ;
    OrS : S -> S -> S ;
    AndNP : NP -> NP -> NP ;
    OrNP : NP -> NP -> NP ;
    PredConjVP : NP -> VP -> VP -> S ;
    PredOrConjVP : NP -> VP -> VP -> S ;
    PredCopNP : NP -> NP -> S ;
    ModifyNP : NP -> PP -> NP ;
    ModifyRel : NP -> V2 -> NP -> NP ;
    ModifyRelVP : NP -> VP -> NP ;
    IndefCN : CN -> NP ;
    DefCN : CN -> NP ;
    ModifyRelCN : CN -> V2 -> NP -> CN ;
    ModifyRelCNVP : CN -> VP -> CN ;
    PossNP : NP -> CN -> NP ;
    EveryCN : String -> String -> NP ;
    OpenAdjDefCN : String -> String -> String -> NP ;
    OpenAdjIndefCN : String -> String -> String -> NP ;
    Announce : V2 ;
    OpenPN : String -> NP ;
    OpenPN2 : String -> String -> NP ;
    OpenPN3 : String -> String -> String -> NP ;
    OpenIndefCN : String -> String -> NP ;
    OpenDefCN : String -> String -> NP ;
    OpenAgentive : V2 ;
    OpenEventive : V2 ;
    OpenArtifactive : V2 ;
    OpenConsumptive : V2 ;
    OpenProductUse : V2 ;
    OpenSourceNP : NP ;
    OpenTargetNP : NP ;
    OpenContextNP : NP ;

    -- Fronted/trailing subordinate clauses ("Because X, Y"/"Y, because
    -- X") -- see grammar/MetonymyEng.gf for why these need SentenceEng's
    -- ExtAdvS/SSubjS specifically (not the plain mkS : Adv -> S -> S
    -- overload, which omits the comma). because_Subj/if_Subj/when_Subj/
    -- although_Subj are closed RGL vocabulary, matching the same
    -- closed-word-per-function idiom already used for the 8 prepositions
    -- above -- no open-ended String parameter, so no PrepPP-class
    -- ambiguity risk.
    BecauseS : S -> S -> S ;
    IfS : S -> S -> S ;
    WhenS : S -> S -> S ;
    AlthoughS : S -> S -> S ;
    SBecauseS : S -> S -> S ;
    SIfS : S -> S -> S ;
    SWhenS : S -> S -> S ;
    SAlthoughS : S -> S -> S ;

    -- Short (1-2 word) comma-delimited appositive ("Waterloo, Ontario,
    -- announces..."), via the same hand-rolled String-concatenation
    -- idiom OpenPN/OpenPN2/OpenPN3 already use -- a literal comma
    -- spliced into the NP's own string, so it plugs directly into the
    -- existing Pred/Compl/PredCopNP with no new S-level machinery.
    -- Deliberately bounded (not a general free-text capture): GF's
    -- String parameter matches exactly one token during parsing, so an
    -- arbitrary-length appositive is not achievable this way -- see
    -- docs/contextual-tower.md for the full reasoning and what was
    -- deliberately deferred.
    ApposCommaPN1 : String -> String -> NP ;
    ApposCommaPN2 : String -> String -> String -> NP ;

    -- Fronted PP adverbial ("On 18 May 2010, Waterloo announces...", "In
    -- 1805, ..."), the same fronted-comma shape as BecauseS/IfS/etc.
    -- Hand-rolled capitalized literals for the same confirmed reason
    -- BecauseS/IfS/WhenS/AlthoughS needed them: InPP/OnPP/FromPP's own
    -- preposition words are hardcoded lowercase (`in_Prep`/`mkPrep
    -- "on"`/`mkPrep "from"`), with no capitalized variant, and this is
    -- the first time any of them needs to appear at a sentence's
    -- absolute start. Covers date/time-fronted sentences, a distinct
    -- and common WiMCor/ConMeC shape.
    OnFrontedS : NP -> S -> S ;
    InFrontedS : NP -> S -> S ;
    FromFrontedS : NP -> S -> S ;

    -- Parenthetical acronym/gloss immediately after an NP ("the Chief
    -- Executive Officer (CEO)", "the Foundation (HOLA)") -- same
    -- hand-rolled String-splicing idiom as ApposCommaPN1/2, parentheses
    -- instead of commas.
    ParenNP : NP -> String -> NP ;

    -- Plain pronoun subjects/objects ("he taught...", "her family...") --
    -- previously entirely unsupported (every NP-building rule before
    -- this needed either a proper noun, a common noun, or a coordination
    -- of those), yet "he"/"his"/etc. are among the single most frequent
    -- tokens a real corpus sentence still fails on. RGL's own closed
    -- Pron vocabulary (Structural.gf, already reachable via the open
    -- Syntax interface) plus mkNP's own `Pron -> NP` overload -- no new
    -- open, no open-ended String parameter.
    HePN : NP ;
    ShePN : NP ;
    ItPN : NP ;
    TheyPN : NP ;

    -- First/second-person pronoun subjects/objects ("I heard...", "we
    -- signed...", "you attended..."), the same closed-vocabulary RGL
    -- Pron idiom as HePN/ShePN/ItPN/TheyPN above -- i_Pron/we_Pron/
    -- youSg_Pron are RGL Structural constants with correct built-in
    -- person/number agreement (confirmed against a real 2026-09-18
    -- corpus-curation round: an earlier hand-rolled `OpenPN "I"`
    -- attempt linearized as the ungrammatical "I hears", because OpenPN
    -- is hardcoded to third-person-singular agreement regardless of the
    -- literal string it's given -- Pron-based NPs don't have that bug).
    -- YouPN covers singular "you" only (youSg_Pron); plural "you" is
    -- indistinguishable from singular in English surface form and rare
    -- as a metonymy target, so not covered separately.
    IPN : NP ;
    WePN : NP ;
    YouPN : NP ;

    -- Bare (determiner-less) common noun NP -- deliberately NOT added.
    -- A real 2026-09-18 corpus-curation round found this would close the
    -- single largest remaining un-representable structural pattern
    -- (~21% of otherwise in-scope real WiMCor/ConMeC sentences: "cars",
    -- "chocolate", bare mass/generic nouns) -- but a first attempt
    -- (`BareSingularCN`/`BarePluralCN : String -> NP`, splicing the noun
    -- in with no fixed anchor word at all, unlike OpenIndefCN/OpenDefCN/
    -- EveryCN which always prepend "a"/"the"/"every") was confirmed via
    -- local `gf.exe -run` against this project's own
    -- test_gf_parse_diagnostic_matrix.py regression sentences to blow up
    -- GF's raw-text parse ambiguity combinatorially (e.g. "Waterloo
    -- announces a general in Hitchin of Hertfordshire" went from a
    -- handful of derivations to 96, and two previously-clean parses
    -- broke outright: "The parser failed at token 7/6"). This only
    -- risks the legacy gf-parser tier's *recall* (a wrong first
    -- candidate degrades to abstain/exit4, same as any other malformed
    -- proposer output) -- Agda's runtimeCheck re-verifies every
    -- candidate regardless of source, so this can never turn into an
    -- incorrect accepted detection -- but the legacy tier is currently
    -- the *dominant* source of real successes in contextual-tower-
    -- evaluation.yml runs, so degrading it isn't free either. Reverted
    -- pending a design that doesn't add an unanchored String NP to the
    -- shared parse-and-linearize PGF (e.g. only reachable from the
    -- Stanza/hand-built tree-construction path, which never calls GF's
    -- own parser at all) -- see docs/contextual-tower.md.

    Anna : NP ;
    Alice : NP ;
    Bob : NP ;
    John : NP ;
    Mary : NP ;
    Tolstoy : NP ;
    WarAndPeace : NP ;
    AnnaKarenina : NP ;
    WorksOfTolstoy : NP ;
    Glass : NP ;
    ContentsOfGlass : NP ;
    Moscow : NP ;
    RussianGovernment : NP ;
    Agreement : NP ;

    Read : V2 ;
    Drink : V2 ;
    Sign : V2 ;
    Have : V2 ;
    Mark : V2 ;
    Empty : V2 ;
    Attend : V2 ;
    Offer : V2 ;
    Publish : V2 ;
    -- Study/Review/Translate/Eat/ListenTo/Watch/Wear/Hear deliberately
    -- NOT declared here: scripts/generate_gf_lexicon.py already emits a
    -- `fun X : V2` (and its `mkV2 "..."` linearization, straight from
    -- data/predicates.tsv's own gf_expression column) for every
    -- predicates.tsv row EXCEPT the three hardcoded ones above
    -- (`base_predicates = {"Read", "Drink", "Sign"}` in that script) --
    -- confirmed by actually running the generator locally and reading
    -- its output, not guessed a second time, after a real CI failure
    -- ("cannot unify ... fun Eat : Metonymy.V2 ; ... fun Eat : V2 ; in
    -- module GeneratedMetonymy") from an earlier attempt to hand-declare
    -- these here too, duplicating what GeneratedMetonymy.gf already
    -- provides. Adding a NEW predicates.tsv row (e.g. "hear") is
    -- therefore sufficient on its own -- no grammar file edit needed at
    -- all, for any lemma outside this three-word exception list.

    Award : V3 ;

    Graduate : V ;
    Work : V ;
    Enroll : V ;
}

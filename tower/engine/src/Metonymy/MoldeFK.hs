-- | A real, three-signal contextual tower: "Molde announced ... signed
-- Kamara on loan for the ... season" (real WiMCor sentence, TEAM medium,
-- see docs/contextual-tower.md's "real sports-club tower" section).
--
-- Unlike Waterloo (two signals, both hard-narrowing), this fixture needed
-- three real, live-Wikidata-verified signals to reach a unique candidate:
-- Molde Municipality (Q104095) hosts two real association football clubs
-- (Molde FK Q208552, the professional Eliteserien club the sentence
-- means, and Bjørset Fotballklubb Q11961495, a real but minor amateur
-- club with almost no further Wikidata coverage) -- confirmed by a live
-- SPARQL query, not assumed. "announce" alone only narrows to
-- Organization (both survive); "season" only narrows to
-- SportsOrganization (both are P31=Q476028, both survive); only "on
-- loan" -- a real phrase in the sentence, and a real distinguishing fact
-- (Molde FK has a live P118 league claim, Bjørset FK has none at all) --
-- narrows to the single correct candidate.
module Metonymy.MoldeFK
  ( moldeTree
  , moldeContextFor
  , moldeSource
  , moldeFK
  , bjorsetFK
  ) where

import Metonymy.Contextual
import Metonymy.Types

-- The hand-built surface this tree is anchored against:
-- "Molde announces a player on a loan and announces a season" -- a
-- deliberately simplified representative form of the real sentence
-- ("Molde announced that they had signed Kamara on loan for the 2015
-- season"), the same simplification style already used for the
-- flagship synthetic towers (docs/contextual-tower.md) -- it carries
-- the same two constraint-bearing lexical items ("loan", "season") in
-- the same two construction positions (ModifyNPObject, ConjClauseObject)
-- as the real sentence, without claiming full syntactic fidelity to the
-- (structurally more complex, embedded-clause) original.
moldeTree :: LexicalTree
moldeTree =
  LexicalApply
    "PredConjVP"
    [ LexicalLeaf (anchor "OpenPN" "molde" "Molde" 0 5) []
    , LexicalApply
        "Compl"
        [ LexicalLeaf
            (anchor "Verb" "announce" "announces" 6 15)
            [Requires (AnyOf [HasSort Animate, HasSort Organization])]
        , LexicalApply
            "ModifyNP"
            [ LexicalLeaf (anchor "Noun" "player" "player" 18 24) []
            , LexicalApply
                "OnPP"
                [ LexicalLeaf
                    (anchor "Noun" "loan" "loan" 30 34)
                    [RequiresSome PlaysInLeague (HasSort Entity)]
                ]
            ]
        ]
    , LexicalApply
        "Compl"
        [ LexicalLeaf (anchor "Verb" "announce" "announces" 39 48) []
        , LexicalLeaf
            (anchor "Noun" "season" "season" 51 57)
            [Requires (HasSort SportsOrganization)]
        ]
    ]

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

moldeContextFor :: Snapshot -> Context
moldeContextFor snapshot =
  Context
    { contextTree = moldeTree
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = moldeSource
    , contextAction = "announce"
    , contextRole = SubjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "announce" "announces" 6 15)
            (Requires (AnyOf [HasSort Animate, HasSort Organization]))
            "VerbNet:say-37.7"
        , ContextConstraint
            (anchor "Noun" "season" "season" 51 57)
            (Requires (HasSort SportsOrganization))
            "wimcor:real:molde-fk-season"
        , ContextConstraint
            (anchor "Noun" "loan" "loan" 30 34)
            (RequiresSome PlaysInLeague (HasSort Entity))
            "wimcor:real:molde-fk-on-loan"
        ]
    , contextRuleProvenance =
        [ "VerbNet:say-37.7"
        , "wimcor:real:molde-fk-season"
        , "wimcor:real:molde-fk-on-loan"
        ]
    }

moldeSource, moldeFK, bjorsetFK :: EntityId
moldeSource = EntityId "Q104095"
moldeFK = EntityId "Q208552"
bjorsetFK = EntityId "Q11961495"

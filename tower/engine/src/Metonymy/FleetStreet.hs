-- | A deliberately-underdetermined place-for-institution example, of a
-- different evidentiary kind from this module's siblings
-- (Metonymy.Waterloo/MoldeFK/Eswatini/Rijeka/AuthorWork): those are each
-- grounded in one real corpus sentence (WiMCor/ConMeC) whose own text
-- happens not to disambiguate further. This one is grounded instead in
-- a documented, ongoing collective usage: "Fleet Street" for the
-- British national press, used even by speakers who know no newspaper
-- has been physically headquartered there since the 1980s-90s --
-- Wikipedia's own Metonymy article states this explicitly, citing
-- Weinreb, Hibbert, Keay & Keay, /The London Encyclopaedia/ (Pan
-- Macmillan, 2008), p. 300. That is the textbook shape of a
-- *deliberately* underdetermined reference (the speaker is not
-- confused about which paper; naming one specific paper would be
-- beside the point), as opposed to the other examples' *accidental*
-- non-uniqueness (the sentence just doesn't happen to say more).
--
-- The sentence itself, "Fleet Street ran the story", is therefore not
-- transcribed from one specific attested text the way the other
-- examples' sentences are -- it is a representative construction of
-- the documented usage pattern above, in the same simplified-for-the-
-- tower style already used throughout this module family (compare
-- Metonymy.AuthorWork's own "he studied Novalis", itself a
-- simplification of its real ConMeC sentence). This should be read and
-- cited accordingly: the *pattern* is corpus/reference-attested, the
-- *sentence* is a representative instance of it, not a found quotation.
--
-- Entities are real: Fleet Street (Q846686), and the three real
-- national newspapers historically headquartered there and confirmed,
-- live, to share Wikidata's "daily newspaper" (Q1110794) class -- Daily
-- Express (Q610190), Daily Mail (Q210534), and The Daily Telegraph
-- (Q192621). The headquarters-location claims themselves (P159 to
-- Fleet Street) are the one departure from this project's usual
-- live-Wikidata-SPARQL discipline: a direct SPARQL query (2026-09-27)
-- confirmed live Wikidata currently has *no* P159/P131/P361 statement
-- connecting any of the three papers to Q846686 -- current statements
-- reflect present-day addresses, not the historical ones this example
-- needs. The P159 claims added to the snapshot for this example are
-- therefore verified against The London Encyclopaedia (cited above),
-- not a live Wikidata claim; this is documented here precisely so
-- nothing downstream mistakes it for the stronger live-SPARQL guarantee
-- the rest of this project maintains elsewhere.
module Metonymy.FleetStreet
  ( fleetStreetContext
  , fleetStreetSource
  , dailyExpress
  , dailyMail
  , dailyTelegraph
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

fleetStreetContext :: Snapshot -> Context
fleetStreetContext snapshot =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "OpenPN" "fleetstreet" "Fleet Street" 0 12) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf (anchor "Verb" "run" "ran" 13 16) []
              , LexicalLeaf
                  (anchor "Noun" "story" "the story" 17 26)
                  [Requires (HasSort Newspaper)]
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = fleetStreetSource
    , contextAction = "run"
    , contextRole = SubjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Noun" "story" "the story" 17 26)
            (Requires (HasSort Newspaper))
            "encyclopaedia:london-encyclopaedia-2008-p300:fleet-street-press"
        ]
    , contextRuleProvenance =
        ["encyclopaedia:london-encyclopaedia-2008-p300:fleet-street-press"]
    }

fleetStreetSource, dailyExpress, dailyMail, dailyTelegraph :: EntityId
fleetStreetSource = EntityId "Q846686"
dailyExpress = EntityId "Q610190"
dailyMail = EntityId "Q210534"
dailyTelegraph = EntityId "Q192621"

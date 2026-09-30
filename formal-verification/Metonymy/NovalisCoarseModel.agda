{-# OPTIONS --cubical #-}

-- A concrete, non-trivial instance of Section "2-truncated compression"
-- (Metonymy.TwoTruncatedContext) against real data, in the same style as
-- Metonymy.ContextualModel's Waterloo fixture: literal Wikidata facts,
-- not a hand-waved signature.
--
-- Real data (same fixture as tower/engine/src/Metonymy/AuthorWork.hs,
-- itself a live-Wikidata-verified real ConMeC sentence, "he studied
-- Novalis" for "... the Romantic poet Novalis, whose Hymns to the Night
-- left a great impression on him"): Novalis (Q60684) has exactly two
-- real P800 notable works, both confirmed via their own P50 (author)
-- claim -- "Hymns to the Night" (Q128670) and "Heinrich von Ofterdingen"
-- (Q58178849), both typed literary works. The Haskell engine's own test
-- suite already documents this as a genuinely non-unique, two-candidate
-- result (Metonymy.AuthorWork's own module comment: "so, honestly, this
-- stays a two-candidate result").
--
-- This module supplies the piece that comment leaves open: a *coarse*
-- reading under which the two candidates ARE identified -- "a work by
-- Novalis" -- without asserting they are the *same* fine candidate. The
-- compatibility relation is the first genuinely non-trivial one
-- instantiated anywhere in this development (contrast
-- Metonymy.TwoTruncatedRuntime.runtimeIdentityCompatibility, which uses
-- bare equality and therefore identifies nothing beyond what was already
-- equal): two candidates are compatible when the first edge of their
-- certificates shares the same source and relation -- "reached from the
-- same entity by the same bridge relation."

module Metonymy.NovalisCoarseModel where

open import Cubical.Foundations.Prelude
open import Cubical.Data.List.Base using (List; []; _∷_)
open import Cubical.Data.Maybe.Base using (Maybe; just; nothing)
open import Cubical.Data.Sigma using (_×_; _,_)
open import Cubical.Data.Unit using (tt)
open import Cubical.HITs.TypeQuotients.Base using (eq/)
open import Agda.Builtin.Bool
open import Agda.Builtin.String
import Agda.Builtin.Equality as Eq

open import Metonymy.Checker
open import Metonymy.FilteredContext
open import Metonymy.FilteredRuntime
open import Metonymy.TwoTruncatedContext

------------------------------------------------------------------------
-- Real data
------------------------------------------------------------------------

novalisKB : KnowledgeBase
novalisKB =
  knowledgeBase
    ( typeFact "Q128670" "LiteraryWork"
    ∷ typeFact "Q58178849" "LiteraryWork"
    ∷ []
    )
    ( relationFact "Authored" "Q60684" "Q128670"
    ∷ relationFact "Authored" "Q60684" "Q58178849"
    ∷ []
    )
    []
    ( predicateFact
        "StudyGF"
        (hasSort "Entity")
        (hasSort "LiteraryWork")
        "HardRequirement"
        "conmec:real:novalis-studied-poet"
    ∷ []
    )
    ( lexemeFact "NovalisGF" "Q60684"
    ∷ lexemeFact "HymnsToTheNightGF" "Q128670"
    ∷ lexemeFact "HeinrichVonOfterdingenGF" "Q58178849"
    ∷ []
    )

beforeClause : RuntimeClause
beforeClause =
  runtimeClause "HePN" "StudyGF" "NovalisGF" defaultForgetContext

afterHymns afterHeinrich : RuntimeClause
afterHymns =
  runtimeClause "HePN" "StudyGF" "HymnsToTheNightGF" defaultForgetContext
afterHeinrich =
  runtimeClause "HePN" "StudyGF" "HeinrichVonOfterdingenGF" defaultForgetContext

certHymns certHeinrich : RawCertificate
certHymns =
  rawCertificate
    expand
    defaultForgetContext
    "StudyGF"
    objectHole
    "Q60684"
    "Q128670"
    (hasSort "LiteraryWork")
    "HardRequirement"
    "conmec:real:novalis-studied-poet"
    (edge "Authored" "Q60684" "Q128670" ∷ [])
certHeinrich =
  rawCertificate
    expand
    defaultForgetContext
    "StudyGF"
    objectHole
    "Q60684"
    "Q58178849"
    (hasSort "LiteraryWork")
    "HardRequirement"
    "conmec:real:novalis-studied-poet"
    (edge "Authored" "Q60684" "Q58178849" ∷ [])

hymnsChecked :
  runtimeCheck novalisKB beforeClause afterHymns certHymns Eq.≡ true
hymnsChecked = Eq.refl

heinrichChecked :
  runtimeCheck novalisKB beforeClause afterHeinrich certHeinrich Eq.≡ true
heinrichChecked = Eq.refl

hymnsAdmissible :
  RuntimeAdmissible novalisKB beforeClause afterHymns certHymns
hymnsAdmissible =
  runtimeCheckSound novalisKB beforeClause afterHymns certHymns hymnsChecked

heinrichAdmissible :
  RuntimeAdmissible novalisKB beforeClause afterHeinrich certHeinrich
heinrichAdmissible =
  runtimeCheckSound
    novalisKB beforeClause afterHeinrich certHeinrich heinrichChecked

------------------------------------------------------------------------
-- The two real candidates, both genuinely admissible
------------------------------------------------------------------------

novalisSystem : PositiveConstraintSystem
novalisSystem = runtimeCandidateSystem novalisKB beforeClause []

hymnsCandidate heinrichCandidate : RuntimeCandidate novalisKB beforeClause
hymnsCandidate = runtimeCandidate afterHymns certHymns
heinrichCandidate = runtimeCandidate afterHeinrich certHeinrich

hymnsFiber heinrichFiber : Fiber novalisSystem []
hymnsFiber = hymnsCandidate , hymnsAdmissible , tt
heinrichFiber = heinrichCandidate , heinrichAdmissible , tt

------------------------------------------------------------------------
-- The non-trivial compatibility relation
------------------------------------------------------------------------

-- "Reached from the same entity by the same bridge relation": the first
-- (here: only) edge of a candidate's certificate, if any.
firstEdgeKey :
  RuntimeCandidate novalisKB beforeClause → Maybe (String × String)
firstEdgeKey candidate
  with RawCertificate.rawEdges (candidateCertificate candidate)
... | [] = nothing
... | (e ∷ _) = just (Edge.edgeRelation e , Edge.edgeSource e)

maybeKeyEqual : Maybe (String × String) → Maybe (String × String) → Bool
maybeKeyEqual nothing nothing = true
maybeKeyEqual (just (r1 , s1)) (just (r2 , s2)) =
  stringEqual r1 r2 and stringEqual s1 s2
maybeKeyEqual _ _ = false

novalisCompatibility : CompatibilitySystem novalisSystem
Compatible novalisCompatibility left right =
  maybeKeyEqual (firstEdgeKey left) (firstEdgeKey right) Eq.≡ true

-- The concrete, non-trivial fact: two *distinct* real Wikidata entities
-- -- Q128670 and Q58178849, neither equal to the other -- are compatible
-- at the coarse level, because both were reached from Q60684 by
-- Authored. This is genuinely new content relative to
-- Metonymy.TwoTruncatedRuntime.runtimeIdentityCompatibility, which never
-- identifies two distinct entities.
hymnsHeinrichCompatible :
  Compatible novalisCompatibility hymnsCandidate heinrichCandidate
hymnsHeinrichCompatible = Eq.refl

------------------------------------------------------------------------
-- 2-cell coherence for this relation
------------------------------------------------------------------------

-- As in Metonymy.TwoTruncatedRuntime.runtimeIdentityCompatibility₂, the
-- 2-cell system is bare (Cubical) path equality between two witnesses;
-- the realization proof is the same `cong` argument, independent of what
-- the underlying Compatible relation happens to be.
novalisCompatibility₂ : Compatibility₂System novalisCompatibility
Compatible₂ novalisCompatibility₂ first second = first ≡ second

novalisCoherence₂ :
  CoherentCompatibility₂ novalisCompatibility novalisCompatibility₂
realizeCompatibility₂ novalisCoherence₂
  {Γ = Γ} {left = left} {right = right} {first = first} {second = second}
  witness =
  cong
    (λ compatibilityWitness →
      cong
        (include₂ {system = novalisSystem} {compatibility = novalisCompatibility} {Γ = Γ})
        (eq/ left right compatibilityWitness))
    witness

------------------------------------------------------------------------
-- The payoff: a genuine identification in Coarse2, for real data
------------------------------------------------------------------------

-- Two distinct real Wikidata entities become one coarse reading: this
-- is a genuine path in Coarse2([]), not a definitional/refl triviality
-- (hymnsFiber and heinrichFiber are not equal as Fiber elements -- their
-- underlying entities, certificates, and edges all differ).
hymnsHeinrichIdentified :
  compress₂ {compatibility = novalisCompatibility} hymnsFiber
    ≡ compress₂ {compatibility = novalisCompatibility} heinrichFiber
hymnsHeinrichIdentified =
  cong
    (include₂ {system = novalisSystem} {compatibility = novalisCompatibility})
    (eq/ hymnsFiber heinrichFiber hymnsHeinrichCompatible)

-- The full bundled 2-truncated tower, instantiated for this real
-- compatibility relation (contrast
-- Metonymy.TwoTruncatedRuntime.runtimeContextual₂Tower, which only ever
-- instantiates it for the trivial identity relation).
novalisContextual₂Tower :
  Contextual₂Tower
    novalisSystem
    (runtimeCandidatePaths novalisKB beforeClause [])
    novalisCompatibility
novalisContextual₂Tower =
  contextual₂Tower
    novalisSystem
    (runtimeCandidatePaths novalisKB beforeClause [])
    novalisCompatibility

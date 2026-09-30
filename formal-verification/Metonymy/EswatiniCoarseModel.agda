{-# OPTIONS --cubical #-}

-- A second non-trivial, real-data instance of 2-truncated compression
-- (see Metonymy.NovalisCoarseModel for the first, and its own comment
-- for the general rationale). Same fixture as
-- tower/engine/src/Metonymy/Eswatini.hs's live-Wikidata-verified real
-- ConMeC sentence, "the cabinet of eSwatini was placed in quarantine",
-- simplified to "Eswatini has a cabinet": a live SPARQL check found 88
-- real P1001 ("applies to jurisdiction") entities for Eswatini (Q1050);
-- Requires (HasSort Government) narrows that to exactly the two real
-- cabinet formations on record -- the Ambrose Mandvulo Dlamini Cabinet
-- (Q114513825) and the Russell Dlamini Cabinet (Q123554307) -- with no
-- further lexical signal in the sentence distinguishing which one (the
-- real distinguishing fact is a date, not a word). The Haskell engine's
-- own test suite already documents this as a genuine two-candidate,
-- non-unique result.
--
-- "A government of Eswatini" -- reached from the same source (Q1050) by
-- the same bridge relation (GovernedBy) -- is exactly as legitimate a
-- coarse reading as Metonymy.NovalisCoarseModel's "a work by Novalis":
-- both cabinet formations are the same kind of thing (a cabinet-level
-- government of the same country), differing only in which specific
-- administration, just as the two Novalis works differ only in which
-- specific text.

module Metonymy.EswatiniCoarseModel where

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

eswatiniKB : KnowledgeBase
eswatiniKB =
  knowledgeBase
    ( typeFact "Q114513825" "Government"
    ∷ typeFact "Q123554307" "Government"
    ∷ []
    )
    ( relationFact "GovernedBy" "Q1050" "Q114513825"
    ∷ relationFact "GovernedBy" "Q1050" "Q123554307"
    ∷ []
    )
    []
    ( predicateFact
        "HaveGF"
        (hasSort "Government")
        (hasSort "Entity")
        "HardRequirement"
        "conmec:real:eswatini-cabinet-quarantine"
    ∷ []
    )
    ( lexemeFact "EswatiniGF" "Q1050"
    ∷ lexemeFact "AmbroseCabinetGF" "Q114513825"
    ∷ lexemeFact "RussellCabinetGF" "Q123554307"
    ∷ []
    )

beforeClause : RuntimeClause
beforeClause =
  runtimeClause "EswatiniGF" "HaveGF" "CabinetGF" defaultForgetContext

afterAmbrose afterRussell : RuntimeClause
afterAmbrose =
  runtimeClause "AmbroseCabinetGF" "HaveGF" "CabinetGF" defaultForgetContext
afterRussell =
  runtimeClause "RussellCabinetGF" "HaveGF" "CabinetGF" defaultForgetContext

certAmbrose certRussell : RawCertificate
certAmbrose =
  rawCertificate
    expand
    defaultForgetContext
    "HaveGF"
    subjectHole
    "Q1050"
    "Q114513825"
    (hasSort "Government")
    "HardRequirement"
    "conmec:real:eswatini-cabinet-quarantine"
    (edge "GovernedBy" "Q1050" "Q114513825" ∷ [])
certRussell =
  rawCertificate
    expand
    defaultForgetContext
    "HaveGF"
    subjectHole
    "Q1050"
    "Q123554307"
    (hasSort "Government")
    "HardRequirement"
    "conmec:real:eswatini-cabinet-quarantine"
    (edge "GovernedBy" "Q1050" "Q123554307" ∷ [])

ambroseChecked :
  runtimeCheck eswatiniKB beforeClause afterAmbrose certAmbrose Eq.≡ true
ambroseChecked = Eq.refl

russellChecked :
  runtimeCheck eswatiniKB beforeClause afterRussell certRussell Eq.≡ true
russellChecked = Eq.refl

ambroseAdmissible :
  RuntimeAdmissible eswatiniKB beforeClause afterAmbrose certAmbrose
ambroseAdmissible =
  runtimeCheckSound eswatiniKB beforeClause afterAmbrose certAmbrose ambroseChecked

russellAdmissible :
  RuntimeAdmissible eswatiniKB beforeClause afterRussell certRussell
russellAdmissible =
  runtimeCheckSound eswatiniKB beforeClause afterRussell certRussell russellChecked

------------------------------------------------------------------------
-- The two real candidates, both genuinely admissible
------------------------------------------------------------------------

eswatiniSystem : PositiveConstraintSystem
eswatiniSystem = runtimeCandidateSystem eswatiniKB beforeClause []

ambroseCandidate russellCandidate :
  RuntimeCandidate eswatiniKB beforeClause
ambroseCandidate = runtimeCandidate afterAmbrose certAmbrose
russellCandidate = runtimeCandidate afterRussell certRussell

ambroseFiber russellFiber : Fiber eswatiniSystem []
ambroseFiber = ambroseCandidate , ambroseAdmissible , tt
russellFiber = russellCandidate , russellAdmissible , tt

------------------------------------------------------------------------
-- The non-trivial compatibility relation (same shape as
-- NovalisCoarseModel's, applied to different real data)
------------------------------------------------------------------------

firstEdgeKey :
  RuntimeCandidate eswatiniKB beforeClause → Maybe (String × String)
firstEdgeKey candidate
  with RawCertificate.rawEdges (candidateCertificate candidate)
... | [] = nothing
... | (e ∷ _) = just (Edge.edgeRelation e , Edge.edgeSource e)

maybeKeyEqual : Maybe (String × String) → Maybe (String × String) → Bool
maybeKeyEqual nothing nothing = true
maybeKeyEqual (just (r1 , s1)) (just (r2 , s2)) =
  stringEqual r1 r2 and stringEqual s1 s2
maybeKeyEqual _ _ = false

eswatiniCompatibility : CompatibilitySystem eswatiniSystem
Compatible eswatiniCompatibility left right =
  maybeKeyEqual (firstEdgeKey left) (firstEdgeKey right) Eq.≡ true

ambroseRussellCompatible :
  Compatible eswatiniCompatibility ambroseCandidate russellCandidate
ambroseRussellCompatible = Eq.refl

------------------------------------------------------------------------
-- 2-cell coherence for this relation
------------------------------------------------------------------------

eswatiniCompatibility₂ : Compatibility₂System eswatiniCompatibility
Compatible₂ eswatiniCompatibility₂ first second = first ≡ second

eswatiniCoherence₂ :
  CoherentCompatibility₂ eswatiniCompatibility eswatiniCompatibility₂
realizeCompatibility₂ eswatiniCoherence₂
  {Γ = Γ} {left = left} {right = right} {first = first} {second = second}
  witness =
  cong
    (λ compatibilityWitness →
      cong
        (include₂ {system = eswatiniSystem} {compatibility = eswatiniCompatibility} {Γ = Γ})
        (eq/ left right compatibilityWitness))
    witness

------------------------------------------------------------------------
-- The payoff: a genuine identification in Coarse2, for real data
------------------------------------------------------------------------

ambroseRussellIdentified :
  compress₂ {compatibility = eswatiniCompatibility} ambroseFiber
    ≡ compress₂ {compatibility = eswatiniCompatibility} russellFiber
ambroseRussellIdentified =
  cong
    (include₂ {system = eswatiniSystem} {compatibility = eswatiniCompatibility})
    (eq/ ambroseFiber russellFiber ambroseRussellCompatible)

eswatiniContextual₂Tower :
  Contextual₂Tower
    eswatiniSystem
    (runtimeCandidatePaths eswatiniKB beforeClause [])
    eswatiniCompatibility
eswatiniContextual₂Tower =
  contextual₂Tower
    eswatiniSystem
    (runtimeCandidatePaths eswatiniKB beforeClause [])
    eswatiniCompatibility

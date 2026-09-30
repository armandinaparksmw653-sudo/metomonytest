{-# OPTIONS --cubical #-}

-- A third non-trivial, real-data instance of 2-truncated compression
-- (see Metonymy.NovalisCoarseModel for the first and its general
-- rationale, Metonymy.EswatiniCoarseModel for the second). Same fixture
-- as tower/engine/src/Metonymy/Rijeka.hs's real WiMCor sentence,
-- "Rijeka announced that Bezjak had signed a three-year contract...",
-- simplified to "Rijeka announces a season": a live SPARQL check found
-- exactly two real football clubs headquartered in Rijeka (Q1647) with
-- a live P118 league claim -- HNK Rijeka (Q318969) and NK Orijent
-- (Q1447572) -- with no lexical signal in the sentence distinguishing
-- which one. The Haskell engine's own test suite documents this as a
-- genuine two-candidate, non-unique result, the same shape as
-- Waterloo/Eswatini/Novalis.
--
-- Unlike those two, Rijeka's disambiguating signal ("season", requiring
-- HasSort SportsOrganization) is a *second*, separate context
-- constraint layered on top of the certificate's own requirement (the
-- verb "announce"'s Animate-or-Organization subject requirement) --
-- the same two-layer shape Metonymy.ContextualModel's Waterloo fixture
-- uses, here exercised through runtimeCandidateSystem's own Constraint/
-- Holds fields (a non-empty context list) rather than a bare Fiber over
-- [].
--
-- "A football club representing Rijeka" -- reached from the same source
-- (Q1647) by the same bridge relation (InstitutionOf) -- is exactly as
-- legitimate a coarse reading as the Novalis/Eswatini cases: this is the
-- standard place-for-team metonymy pattern (cf. "Chelsea signed...",
-- "Liverpool won..."), not an arbitrary conflation of two unrelated
-- organizations -- both candidates are the same kind of thing (a
-- top-flight football club based in the same city), differing only in
-- which specific club.

module Metonymy.RijekaCoarseModel where

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

rijekaKB : KnowledgeBase
rijekaKB =
  knowledgeBase
    ( typeFact "Q318969" "Organization"
    ∷ typeFact "Q318969" "SportsOrganization"
    ∷ typeFact "Q1447572" "Organization"
    ∷ typeFact "Q1447572" "SportsOrganization"
    ∷ []
    )
    ( relationFact "InstitutionOf" "Q1647" "Q318969"
    ∷ relationFact "InstitutionOf" "Q1647" "Q1447572"
    ∷ []
    )
    []
    ( predicateFact
        "AnnounceGF"
        (anyOf (hasSort "Animate" ∷ hasSort "Organization" ∷ []))
        (hasSort "Entity")
        "HardRequirement"
        "VerbNet:say-37.7"
    ∷ []
    )
    ( lexemeFact "RijekaGF" "Q1647"
    ∷ lexemeFact "HNKRijekaGF" "Q318969"
    ∷ lexemeFact "NKOrijentGF" "Q1447572"
    ∷ []
    )

beforeClause : RuntimeClause
beforeClause =
  runtimeClause "RijekaGF" "AnnounceGF" "SeasonGF" defaultForgetContext

afterHNK afterOrijent : RuntimeClause
afterHNK =
  runtimeClause "HNKRijekaGF" "AnnounceGF" "SeasonGF" defaultForgetContext
afterOrijent =
  runtimeClause "NKOrijentGF" "AnnounceGF" "SeasonGF" defaultForgetContext

certHNK certOrijent : RawCertificate
certHNK =
  rawCertificate
    expand
    defaultForgetContext
    "AnnounceGF"
    subjectHole
    "Q1647"
    "Q318969"
    (anyOf (hasSort "Animate" ∷ hasSort "Organization" ∷ []))
    "HardRequirement"
    "VerbNet:say-37.7"
    (edge "InstitutionOf" "Q1647" "Q318969" ∷ [])
certOrijent =
  rawCertificate
    expand
    defaultForgetContext
    "AnnounceGF"
    subjectHole
    "Q1647"
    "Q1447572"
    (anyOf (hasSort "Animate" ∷ hasSort "Organization" ∷ []))
    "HardRequirement"
    "VerbNet:say-37.7"
    (edge "InstitutionOf" "Q1647" "Q1447572" ∷ [])

hnkChecked :
  runtimeCheck rijekaKB beforeClause afterHNK certHNK Eq.≡ true
hnkChecked = Eq.refl

orijentChecked :
  runtimeCheck rijekaKB beforeClause afterOrijent certOrijent Eq.≡ true
orijentChecked = Eq.refl

hnkAdmissible :
  RuntimeAdmissible rijekaKB beforeClause afterHNK certHNK
hnkAdmissible =
  runtimeCheckSound rijekaKB beforeClause afterHNK certHNK hnkChecked

orijentAdmissible :
  RuntimeAdmissible rijekaKB beforeClause afterOrijent certOrijent
orijentAdmissible =
  runtimeCheckSound rijekaKB beforeClause afterOrijent certOrijent orijentChecked

------------------------------------------------------------------------
-- The second, layered constraint ("season" requires SportsOrganization)
------------------------------------------------------------------------

seasonAnchor : RawLexicalAnchor
seasonAnchor = rawLexicalAnchor "Noun" "season" "season" 19 25

rijekaRules : List String
rijekaRules = "wimcor:real:rijeka-season" ∷ []

seasonConstraint : RawContextConstraint
seasonConstraint =
  rawContextConstraint
    seasonAnchor
    (rawRequires (hasSort "SportsOrganization"))
    "wimcor:real:rijeka-season"

rijekaΓ : List RawContextConstraint
rijekaΓ = seasonConstraint ∷ []

rijekaSystem : PositiveConstraintSystem
rijekaSystem = runtimeCandidateSystem rijekaKB beforeClause rijekaRules

hnkCandidate orijentCandidate : RuntimeCandidate rijekaKB beforeClause
hnkCandidate = runtimeCandidate afterHNK certHNK
orijentCandidate = runtimeCandidate afterOrijent certOrijent

hnkSeasonHolds :
  Holds rijekaSystem hnkCandidate seasonConstraint
hnkSeasonHolds = Eq.refl

orijentSeasonHolds :
  Holds rijekaSystem orijentCandidate seasonConstraint
orijentSeasonHolds = Eq.refl

hnkFiber orijentFiber : Fiber rijekaSystem rijekaΓ
hnkFiber = hnkCandidate , hnkAdmissible , hnkSeasonHolds , tt
orijentFiber = orijentCandidate , orijentAdmissible , orijentSeasonHolds , tt

------------------------------------------------------------------------
-- The non-trivial compatibility relation (same shape as
-- NovalisCoarseModel/EswatiniCoarseModel's, applied to different real
-- data)
------------------------------------------------------------------------

firstEdgeKey :
  RuntimeCandidate rijekaKB beforeClause → Maybe (String × String)
firstEdgeKey candidate
  with RawCertificate.rawEdges (candidateCertificate candidate)
... | [] = nothing
... | (e ∷ _) = just (Edge.edgeRelation e , Edge.edgeSource e)

maybeKeyEqual : Maybe (String × String) → Maybe (String × String) → Bool
maybeKeyEqual nothing nothing = true
maybeKeyEqual (just (r1 , s1)) (just (r2 , s2)) =
  stringEqual r1 r2 and stringEqual s1 s2
maybeKeyEqual _ _ = false

rijekaCompatibility : CompatibilitySystem rijekaSystem
Compatible rijekaCompatibility left right =
  maybeKeyEqual (firstEdgeKey left) (firstEdgeKey right) Eq.≡ true

hnkOrijentCompatible :
  Compatible rijekaCompatibility hnkCandidate orijentCandidate
hnkOrijentCompatible = Eq.refl

------------------------------------------------------------------------
-- 2-cell coherence for this relation
------------------------------------------------------------------------

rijekaCompatibility₂ : Compatibility₂System rijekaCompatibility
Compatible₂ rijekaCompatibility₂ first second = first ≡ second

rijekaCoherence₂ :
  CoherentCompatibility₂ rijekaCompatibility rijekaCompatibility₂
realizeCompatibility₂ rijekaCoherence₂
  {Γ = Γ} {left = left} {right = right} {first = first} {second = second}
  witness =
  cong
    (λ compatibilityWitness →
      cong
        (include₂ {system = rijekaSystem} {compatibility = rijekaCompatibility} {Γ = Γ})
        (eq/ left right compatibilityWitness))
    witness

------------------------------------------------------------------------
-- The payoff: a genuine identification in Coarse2, for real data, at a
-- non-empty context (both candidates already satisfy the same "season"
-- signal, and are identified anyway -- compression does not compete
-- with narrowing, it only applies once narrowing is exhausted)
------------------------------------------------------------------------

hnkOrijentIdentified :
  compress₂ {system = rijekaSystem} {compatibility = rijekaCompatibility} {Γ = rijekaΓ} hnkFiber
    ≡ compress₂ {system = rijekaSystem} {compatibility = rijekaCompatibility} {Γ = rijekaΓ} orijentFiber
hnkOrijentIdentified =
  cong
    (include₂ {system = rijekaSystem} {compatibility = rijekaCompatibility} {Γ = rijekaΓ})
    (eq/ hnkFiber orijentFiber hnkOrijentCompatible)

rijekaContextual₂Tower :
  Contextual₂Tower
    rijekaSystem
    (runtimeCandidatePaths rijekaKB beforeClause rijekaRules)
    rijekaCompatibility
rijekaContextual₂Tower =
  contextual₂Tower
    rijekaSystem
    (runtimeCandidatePaths rijekaKB beforeClause rijekaRules)
    rijekaCompatibility

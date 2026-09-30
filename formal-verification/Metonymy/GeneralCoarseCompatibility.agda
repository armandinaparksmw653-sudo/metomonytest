{-# OPTIONS --cubical #-}

-- The general, engine-exposed version of the coarse-reading compatibility
-- relation that Metonymy.NovalisCoarseModel/EswatiniCoarseModel/
-- RijekaCoarseModel each hand-built as one-off examples: this module
-- shows Checker.compatibilityCheck genuinely instantiates the
-- 2-truncated compression machinery (Metonymy.TwoTruncatedContext) for
-- *any* pair of certificates, not just those three, and -- just as
-- important -- proves the safety property that motivated the "single
-- HasSort only" restriction: a heterogeneous pair that satisfies only a
-- broad AnyOf requirement (the Waterloo fixture's "announce" requirement,
-- before its narrowing "in physics" signal is applied) is correctly
-- rejected, not silently merged.

module Metonymy.GeneralCoarseCompatibility where

open import Cubical.Foundations.Prelude
open import Cubical.Data.List.Base using (List; []; _∷_)
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
-- The general compatibility system: parametric in any knowledge base,
-- "before" clause, and rule list -- built directly from
-- Checker.compatibilityCheck, the same function the engine calls.
------------------------------------------------------------------------

generalCompatibility :
  (kb : KnowledgeBase) (before : RuntimeClause) (rules : List String) →
  CompatibilitySystem (runtimeCandidateSystem kb before rules)
Compatible (generalCompatibility kb before rules) left right =
  compatibilityCheck
    (candidateCertificate left)
    (candidateCertificate right)
    Eq.≡ true

-- Same generic 2-cell coherence argument as
-- Metonymy.TwoTruncatedRuntime.runtimeIdentityCoherence₂ and each of the
-- three coarse-model instances: bare (Cubical) path equality between two
-- witnesses, independent of what the underlying Boolean check is.
generalCompatibility₂ :
  (kb : KnowledgeBase) (before : RuntimeClause) (rules : List String) →
  Compatibility₂System (generalCompatibility kb before rules)
Compatible₂ (generalCompatibility₂ kb before rules) first second =
  first ≡ second

generalCoherence₂ :
  (kb : KnowledgeBase) (before : RuntimeClause) (rules : List String) →
  CoherentCompatibility₂
    (generalCompatibility kb before rules)
    (generalCompatibility₂ kb before rules)
realizeCompatibility₂ (generalCoherence₂ kb before rules)
  {Γ = Γ} {left = left} {right = right} {first = first} {second = second}
  witness =
  cong
    (λ compatibilityWitness →
      cong
        ( include₂
            {system = runtimeCandidateSystem kb before rules}
            {compatibility = generalCompatibility kb before rules}
            {Γ = Γ}
        )
        (eq/ left right compatibilityWitness))
    witness

-- The general payoff: whenever the engine's own compatibilityCheck
-- accepts two candidates, they are identified in Coarse2 -- for any
-- knowledge base, not just the three curated ones.
generalIdentified :
  (kb : KnowledgeBase) (before : RuntimeClause) (rules : List String) →
  (Γ : Context (runtimeCandidateSystem kb before rules)) →
  (leftFiber rightFiber : Fiber (runtimeCandidateSystem kb before rules) Γ) →
  compatibilityCheck
    (candidateCertificate (candidate (runtimeCandidateSystem kb before rules) leftFiber))
    (candidateCertificate (candidate (runtimeCandidateSystem kb before rules) rightFiber))
    Eq.≡ true →
  compress₂
    {system = runtimeCandidateSystem kb before rules}
    {compatibility = generalCompatibility kb before rules}
    {Γ = Γ} leftFiber
    ≡
  compress₂
    {system = runtimeCandidateSystem kb before rules}
    {compatibility = generalCompatibility kb before rules}
    {Γ = Γ} rightFiber
generalIdentified kb before rules Γ leftFiber rightFiber checked =
  cong
    ( include₂
        {system = runtimeCandidateSystem kb before rules}
        {compatibility = generalCompatibility kb before rules}
        {Γ = Γ}
    )
    (eq/ leftFiber rightFiber checked)

------------------------------------------------------------------------
-- Safety property: a heterogeneous pair satisfying only a broad AnyOf
-- requirement is correctly rejected, using the real Waterloo fixture's
-- own data (Metonymy.ContextualModel) -- University of Waterloo
-- (Q1049470) and Waterloo City Council (Q7974219), both admissible under
-- "announce"'s AnyOf [Animate, Organization] requirement alone, before
-- the sentence's second, narrowing "in physics" signal is applied.
------------------------------------------------------------------------

waterlooAnnounceRequirement : Requirement
waterlooAnnounceRequirement =
  anyOf (hasSort "Animate" ∷ hasSort "Organization" ∷ [])

universityCertificate councilCertificate : RawCertificate
universityCertificate =
  rawCertificate
    expand
    defaultForgetContext
    "AnnounceGF"
    subjectHole
    "Q639408"
    "Q1049470"
    waterlooAnnounceRequirement
    "HardRequirement"
    "contextual-rules-1"
    (edge "InstitutionOf" "Q639408" "Q1049470" ∷ [])
councilCertificate =
  rawCertificate
    expand
    defaultForgetContext
    "AnnounceGF"
    subjectHole
    "Q639408"
    "Q7974219"
    waterlooAnnounceRequirement
    "HardRequirement"
    "contextual-rules-1"
    (edge "InstitutionOf" "Q639408" "Q7974219" ∷ [])

-- Same source, same relation -- exactly the shape the compatibility
-- check would accept for a single HasSort. It is rejected anyway,
-- because the requirement that selected both is AnyOf, not HasSort: two
-- organizations of genuinely different kinds must never be reported as
-- one coarse reading merely for sharing a broad disjunctive requirement.
universityCouncilNotCompatible :
  compatibilityCheck universityCertificate councilCertificate Eq.≡ false
universityCouncilNotCompatible = Eq.refl

-- The specific reason, isolated: the requirement itself is not a single
-- HasSort.
waterlooRequirementNotSingleSort :
  isSingleHasSort waterlooAnnounceRequirement Eq.≡ false
waterlooRequirementNotSingleSort = Eq.refl

------------------------------------------------------------------------
-- Cross-check: the general checker accepts the same real pairs the
-- three hand-built examples already proved compatible (same source,
-- same relation, single matching HasSort) -- confirming the
-- generalization reproduces the specific results, not just the negative
-- case above.
------------------------------------------------------------------------

novalisHardRequirement : Requirement
novalisHardRequirement = hasSort "LiteraryWork"

hymnsCertificateGeneral heinrichCertificateGeneral : RawCertificate
hymnsCertificateGeneral =
  rawCertificate
    expand
    defaultForgetContext
    "StudyGF"
    objectHole
    "Q60684"
    "Q128670"
    novalisHardRequirement
    "HardRequirement"
    "conmec:real:novalis-studied-poet"
    (edge "Authored" "Q60684" "Q128670" ∷ [])
heinrichCertificateGeneral =
  rawCertificate
    expand
    defaultForgetContext
    "StudyGF"
    objectHole
    "Q60684"
    "Q58178849"
    novalisHardRequirement
    "HardRequirement"
    "conmec:real:novalis-studied-poet"
    (edge "Authored" "Q60684" "Q58178849" ∷ [])

generalCheckerAcceptsNovalis :
  compatibilityCheck hymnsCertificateGeneral heinrichCertificateGeneral
    Eq.≡ true
generalCheckerAcceptsNovalis = Eq.refl

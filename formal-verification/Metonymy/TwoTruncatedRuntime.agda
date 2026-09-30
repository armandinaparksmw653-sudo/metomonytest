{-# OPTIONS --cubical #-}

module Metonymy.TwoTruncatedRuntime where

open import Cubical.Foundations.Prelude
open import Cubical.Data.List.Base using (List)
open import Cubical.HITs.TypeQuotients.Base
  renaming (eq/ to eq/h)
open import Agda.Builtin.String

open import Metonymy.Checker
open import Metonymy.FilteredContext
open import Metonymy.FilteredRuntime
open import Metonymy.TwoTruncatedContext

runtimeIdentityCompatibility :
  (kb : KnowledgeBase) →
  (before : RuntimeClause) →
  (rules : List String) →
  CompatibilitySystem (runtimeCandidateSystem kb before rules)
Compatible (runtimeIdentityCompatibility kb before rules) left right =
  left ≡ right

runtimeIdentityCompatibility₂ :
  (kb : KnowledgeBase) →
  (before : RuntimeClause) →
  (rules : List String) →
  Compatibility₂System
    (runtimeIdentityCompatibility kb before rules)
Compatible₂
  (runtimeIdentityCompatibility₂ kb before rules)
  first second =
  first ≡ second

runtimeIdentityCoherence₂ :
  (kb : KnowledgeBase) →
  (before : RuntimeClause) →
  (rules : List String) →
  CoherentCompatibility₂
    (runtimeIdentityCompatibility kb before rules)
    (runtimeIdentityCompatibility₂ kb before rules)
realizeCompatibility₂
  (runtimeIdentityCoherence₂ kb before rules)
  {Γ = Γ}
  {left = left}
  {right = right}
  {first = first}
  {second = second}
  witness =
  cong
    (λ compatibilityWitness →
      cong
        (include₂
          {system = runtimeCandidateSystem kb before rules}
          {compatibility = runtimeIdentityCompatibility kb before rules}
          {Γ = Γ})
        (eq/h left right compatibilityWitness))
    witness

runtimeContextual₂Tower :
  (kb : KnowledgeBase) →
  (before : RuntimeClause) →
  (rules : List String) →
  Contextual₂Tower
    (runtimeCandidateSystem kb before rules)
    (runtimeCandidatePaths kb before rules)
    (runtimeIdentityCompatibility kb before rules)
runtimeContextual₂Tower kb before rules =
  contextual₂Tower
    (runtimeCandidateSystem kb before rules)
    (runtimeCandidatePaths kb before rules)
    (runtimeIdentityCompatibility kb before rules)

{-# OPTIONS --cubical #-}

module Metonymy.TwoTruncatedContext where

open import Cubical.Foundations.Prelude
open import Cubical.Foundations.HLevels
open import Cubical.HITs.TypeQuotients.Base
  renaming (_/ₜ_ to _/h_; [_] to [_]h; eq/ to eq/h)
import Cubical.HITs.TypeQuotients.Properties as HQ
open import Cubical.HITs.2GroupoidTruncation.Base
  renaming (∥_∥₄ to ∥_∥₂; ∣_∣₄ to ∣_∣₂; squash₄ to squash₂)
import Cubical.HITs.2GroupoidTruncation.Properties as Trunc₂

open import Metonymy.FilteredContext

RawCoarse₂ :
  {system : PositiveConstraintSystem} →
  CompatibilitySystem system →
  Context system →
  Type
RawCoarse₂ {system} compatibility Γ =
  Fiber system Γ /h FiberCompatible system compatibility

Coarse₂ :
  {system : PositiveConstraintSystem} →
  CompatibilitySystem system →
  Context system →
  Type
Coarse₂ compatibility Γ =
  ∥ RawCoarse₂ compatibility Γ ∥₂

is2GroupoidCoarse₂ :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {Γ : Context system} →
  is2Groupoid (Coarse₂ compatibility Γ)
is2GroupoidCoarse₂ =
  Trunc₂.is2Groupoid2GroupoidTrunc

include₂ :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {Γ : Context system} →
  RawCoarse₂ compatibility Γ →
  Coarse₂ compatibility Γ
include₂ value =
  ∣ value ∣₂

compressRaw₂ :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {Γ : Context system} →
  Fiber system Γ →
  RawCoarse₂ compatibility Γ
compressRaw₂ =
  [_]h

compress₂ :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {Γ : Context system} →
  Fiber system Γ →
  Coarse₂ compatibility Γ
compress₂ {system} {compatibility} value =
  include₂ {system = system} {compatibility = compatibility}
    (compressRaw₂ {system = system} {compatibility = compatibility} value)

restrictRawCoarse₂ :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {weaker stronger : Context system} →
  Refinement system weaker stronger →
  RawCoarse₂ compatibility stronger →
  RawCoarse₂ compatibility weaker
restrictRawCoarse₂ {system} {compatibility} map =
  HQ.rec
    (λ value →
      compressRaw₂ {system = system} {compatibility = compatibility}
        (restrict {system = system} map value))
    (λ left right witness →
      eq/h
        (restrict {system = system} map left)
        (restrict {system = system} map right)
        (restrictPreservesCompatibility
          {system = system}
          {compatibility = compatibility}
          map
          {left = left}
          {right = right}
          witness))

restrictCoarse₂ :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {weaker stronger : Context system} →
  Refinement system weaker stronger →
  Coarse₂ compatibility stronger →
  Coarse₂ compatibility weaker
restrictCoarse₂ {system} {compatibility = compatibility} map =
  Trunc₂.rec
    (is2GroupoidCoarse₂ {system = system} {compatibility = compatibility})
    (λ value →
      include₂ {system = system} {compatibility = compatibility}
        (restrictRawCoarse₂
          {system = system}
          {compatibility = compatibility}
          map value))

compression₂Naturality :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {weaker stronger : Context system} →
  (map : Refinement system weaker stronger) →
  (value : Fiber system stronger) →
  restrictCoarse₂ {compatibility = compatibility} map
    (compress₂ {compatibility = compatibility} value)
    ≡
  compress₂ {compatibility = compatibility}
    (restrict {system = system} map value)
compression₂Naturality map value =
  refl

coarse₂IdentityOnGenerator :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {Γ : Context system} →
  (value : Fiber system Γ) →
  restrictCoarse₂ {compatibility = compatibility}
    (identityRefinement {system = system})
    (compress₂ {compatibility = compatibility} value)
    ≡ compress₂ {compatibility = compatibility} value
coarse₂IdentityOnGenerator {system} {compatibility = compatibility} value =
  cong
    (λ endpoint →
      compress₂ {compatibility = compatibility} endpoint)
    (restrictIdentity {system = system} value)

coarse₂CompositionOnGenerator :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {weak middle strong : Context system} →
  (first : Refinement system weak middle) →
  (second : Refinement system middle strong) →
  (value : Fiber system strong) →
  restrictCoarse₂ {compatibility = compatibility}
    (composeRefinement first second)
    (compress₂ {compatibility = compatibility} value)
    ≡
  restrictCoarse₂ {compatibility = compatibility} first
    ( restrictCoarse₂ {compatibility = compatibility} second
      (compress₂ {compatibility = compatibility} value)
    )
coarse₂CompositionOnGenerator
  {system} {compatibility = compatibility} first second value =
  cong
    (λ endpoint →
      compress₂ {compatibility = compatibility} endpoint)
    (restrictComposition {system = system} first second value)

record Compatibility₂System
  {system : PositiveConstraintSystem}
  (compatibility : CompatibilitySystem system) : Type₁ where
  field
    Compatible₂ :
      {left right : Entity system} →
      Compatible compatibility left right →
      Compatible compatibility left right →
      Type

open Compatibility₂System public

FiberCompatibility₂ :
  (system : PositiveConstraintSystem) →
  (compatibility : CompatibilitySystem system) →
  Compatibility₂System compatibility →
  {Γ : Context system} →
  {left right : Fiber system Γ} →
  (first second : FiberCompatible system compatibility left right) →
  Type
FiberCompatibility₂ system compatibility coherence
  {left = left} {right = right} first second =
  Compatible₂ coherence
    {left = candidate system left}
    {right = candidate system right}
    first second

record CoherentCompatibility₂
  {system : PositiveConstraintSystem}
  (compatibility : CompatibilitySystem system)
  (coherence : Compatibility₂System compatibility) : Type₁ where
  field
    realizeCompatibility₂ :
      {Γ : Context system} →
      {left right : Fiber system Γ} →
      {first second : FiberCompatible system compatibility left right} →
      FiberCompatibility₂ system compatibility coherence
        {Γ = Γ}
        {left = left}
        {right = right}
        first second →
      cong
        (include₂
          {system = system}
          {compatibility = compatibility}
          {Γ = Γ})
        (eq/h left right first)
        ≡
      cong
        (include₂
          {system = system}
          {compatibility = compatibility}
          {Γ = Γ})
        (eq/h left right second)

open CoherentCompatibility₂ public

record Coarse₂Pseudofunctor
  (system : PositiveConstraintSystem)
  (compatibility : CompatibilitySystem system) : Type₁ where
  field
    map₂ :
      {weaker stronger : Context system} →
      Refinement system weaker stronger →
      Coarse₂ compatibility stronger →
      Coarse₂ compatibility weaker
    identity₂ :
      {Γ : Context system} →
      (value : Coarse₂ compatibility Γ) →
      map₂ identityRefinement value ≡ value
    composition₂ :
      {weak middle strong : Context system} →
      (first : Refinement system weak middle) →
      (second : Refinement system middle strong) →
      (value : Coarse₂ compatibility strong) →
      map₂ (composeRefinement first second) value
        ≡ map₂ first (map₂ second value)

open Coarse₂Pseudofunctor public

coherenceAboveDimension₂ :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {Γ : Context system} →
  (x y : Coarse₂ compatibility Γ) →
  (first second : x ≡ y) →
  (left right : first ≡ second) →
  (one two : left ≡ right) →
  one ≡ two
coherenceAboveDimension₂ =
  squash₂

record Contextual₂Tower
  (system : PositiveConstraintSystem)
  (paths : PathSystem system)
  (compatibility : CompatibilitySystem system) : Type₁ where
  field
    fineTower :
      ContextualHomotopyTower system paths compatibility
    coarse₂Map :
      {weaker stronger : Context system} →
      Refinement system weaker stronger →
      Coarse₂ compatibility stronger →
      Coarse₂ compatibility weaker
    compression₂Natural :
      {weaker stronger : Context system} →
      (map : Refinement system weaker stronger) →
      (value : Fiber system stronger) →
      coarse₂Map map (compress₂ {compatibility = compatibility} value)
        ≡
      compress₂ {compatibility = compatibility}
        (restrict {system = system} map value)

contextual₂Tower :
  (system : PositiveConstraintSystem) →
  (paths : PathSystem system) →
  (compatibility : CompatibilitySystem system) →
  Contextual₂Tower system paths compatibility
Contextual₂Tower.fineTower
  (contextual₂Tower system paths compatibility) =
  contextualHomotopyTower system paths compatibility
Contextual₂Tower.coarse₂Map
  (contextual₂Tower system paths compatibility) =
  restrictCoarse₂ {compatibility = compatibility}
Contextual₂Tower.compression₂Natural
  (contextual₂Tower system paths compatibility) =
  compression₂Naturality {compatibility = compatibility}

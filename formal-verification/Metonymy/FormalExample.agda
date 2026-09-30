{-# OPTIONS --cubical #-}

module Metonymy.FormalExample where

open import Cubical.Foundations.Prelude
open import Cubical.Data.Unit
open import Metonymy.Grammar
open import Metonymy.Cell
open import Metonymy.Completion
open import Metonymy.Semantics

data Interface₀ : Type where
  readStart readDone : Interface₀

data Rule₀ : Interface₀ → Interface₀ → Type where
  mentionTolstoy :
    Rule₀ readStart readDone

  mentionWorks :
    Rule₀ readStart readDone

Grammar₀ : GrammarSignature
Interface Grammar₀ = Interface₀
Rule Grammar₀ = Rule₀

implicitReading :
  RawDerivation Grammar₀ readStart readDone
implicitReading =
  rule mentionTolstoy

explicitReading :
  RawDerivation Grammar₀ readStart readDone
explicitReading =
  rule mentionWorks

data HardCell₀ :
  {A B : Interface₀} →
  RawDerivation Grammar₀ A B →
  RawDerivation Grammar₀ A B →
  Type where

  identity₀ :
    {A B : Interface₀} →
    (f : RawDerivation Grammar₀ A B) →
    HardCell₀ f f

  authorToWorks :
    HardCell₀ implicitReading explicitReading

  compose₀ :
    {A B C : Interface₀} →
    {f f' : RawDerivation Grammar₀ A B} →
    {g g' : RawDerivation Grammar₀ B C} →
    HardCell₀ f f' →
    HardCell₀ g g' →
    HardCell₀ (f then g) (f' then g')

data PreferredCell₀ :
  {A B : Interface₀} →
  RawDerivation Grammar₀ A B →
  RawDerivation Grammar₀ A B →
  Type where

  preferredAuthorToWorks :
    PreferredCell₀ implicitReading explicitReading

data Basic₂₀ :
  {A B : Interface₀} →
  {f g : RawDerivation Grammar₀ A B} →
  HardCell₀ f g →
  HardCell₀ f g →
  Type where

  sameCell :
    {A B : Interface₀} →
    {f g : RawDerivation Grammar₀ A B} →
    {cell : HardCell₀ f g} →
    Basic₂₀ cell cell

System₀ : MetonymicSystem Grammar₀
HardCell System₀ = HardCell₀
PreferredCell System₀ = PreferredCell₀
PromotionEvidence System₀ preferred = Unit
promote System₀ preferredAuthorToWorks tt =
  authorToWorks
Basic₂ System₀ =
  Basic₂₀

hardExamplePath :
  Path
    (Completion System₀ readStart readDone)
    (raw implicitReading)
    (raw explicitReading)
hardExamplePath =
  metonymic authorToWorks

preferredRequiresEvidence :
  PreferredCell System₀ implicitReading explicitReading
preferredRequiresEvidence =
  preferredAuthorToWorks

promotedExamplePath :
  Path
    (Completion System₀ readStart readDone)
    (raw implicitReading)
    (raw explicitReading)
promotedExamplePath =
  promotedPath preferredAuthorToWorks tt

constantSemantics :
  SemanticModel System₀ readStart readDone
Meaning constantSemantics =
  Unit
interpretRaw constantSemantics derivation =
  tt
respectCell constantSemantics cell =
  refl
respectCoherence constantSemantics square =
  refl

exampleFactorization :
  interpret constantSemantics (raw implicitReading)
    ≡
  interpretRaw constantSemantics implicitReading
exampleFactorization =
  factorization constantSemantics implicitReading

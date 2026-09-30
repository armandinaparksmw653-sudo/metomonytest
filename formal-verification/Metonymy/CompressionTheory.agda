{-# OPTIONS --cubical #-}

module Metonymy.CompressionTheory where

open import Cubical.Foundations.Prelude
open import Cubical.Data.Empty
open import Cubical.HITs.TypeQuotients.Properties as Quotient
open import Metonymy.Ontology
open import Metonymy.Compression

infix 3 _≢_

_≢_ : {A : Type} → A → A → Type
left ≢ right =
  left ≡ right → ⊥

record CompressionModel
  {O : OntologySignature}
  {R : ResolutionSignature O}
  (C : CompressionSignature O R)
  (Γ : Context R)
  (K : Hole R)
  (source : Entity O) : Type₁ where

  field
    Meaning : Type

    classify :
      Fine Γ K source →
      Meaning

    respectCompatibility :
      (left right : Fine Γ K source) →
      SameMetonymicClass C left right →
      classify left ≡ classify right

open CompressionModel public

classifyCoarse :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  (model : CompressionModel C Γ K source) →
  Coarse C Γ K source →
  Meaning model
classifyCoarse model =
  Quotient.rec
    (classify model)
    (respectCompatibility model)

classificationFactors :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  (model : CompressionModel C Γ K source) →
  (explicitValue : Fine Γ K source) →
  classifyCoarse model (contract {C = C} explicitValue)
    ≡
  classify model explicitValue
classificationFactors model explicitValue =
  refl

separatedCompressedMeanings :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  (model : CompressionModel C Γ K source) →
  (left right : Fine Γ K source) →
  classify model left ≢ classify model right →
  contract {C = C} left ≢ contract {C = C} right
separatedCompressedMeanings model left right meaningsDiffer path =
  meaningsDiffer (cong (classifyCoarse model) path)

record UniqueExpansion
  {O : OntologySignature}
  {R : ResolutionSignature O}
  {C : CompressionSignature O R}
  {Γ : Context R}
  {K : Hole R}
  {source : Entity O}
  (coarse : Coarse C Γ K source) : Type where

  field
    representative :
      Fine Γ K source

    represents :
      contract {C = C} representative ≡ coarse

    unique :
      (candidate : Fine Γ K source) →
      contract {C = C} candidate ≡ coarse →
      candidate ≡ representative

open UniqueExpansion public

uniqueRoundTrip :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  (explicitValue : Fine Γ K source) →
  ( uniqueness :
      UniqueExpansion {C = C}
        (contract {C = C} explicitValue)
  ) →
  representative uniqueness ≡ explicitValue
uniqueRoundTrip explicitValue uniqueness =
  sym
    ( unique uniqueness explicitValue
        refl
    )

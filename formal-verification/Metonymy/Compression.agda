{-# OPTIONS --cubical #-}

module Metonymy.Compression where

open import Cubical.Foundations.Prelude
open import Cubical.Data.Sigma
open import Cubical.HITs.TypeQuotients.Base
open import Metonymy.Ontology

record CompressionSignature
  (O : OntologySignature)
  (R : ResolutionSignature O) : Type₁ where

  field
    TargetCompatible :
      (Γ : Context R) →
      (K : Hole R) →
      (left right : Entity O) →
      Type

    targetCompatibleRefl :
      {Γ : Context R} →
      {K : Hole R} →
      {target : Entity O} →
      Fits R Γ K target →
      TargetCompatible Γ K target target

    targetCompatibleSym :
      {Γ : Context R} →
      {K : Hole R} →
      {left right : Entity O} →
      Fits R Γ K left →
      Fits R Γ K right →
      TargetCompatible Γ K left right →
      TargetCompatible Γ K right left

    targetCompatibleTrans :
      {Γ : Context R} →
      {K : Hole R} →
      {first second third : Entity O} →
      Fits R Γ K first →
      Fits R Γ K second →
      Fits R Γ K third →
      TargetCompatible Γ K first second →
      TargetCompatible Γ K second third →
      TargetCompatible Γ K first third

open CompressionSignature public

record Fine
  {O : OntologySignature}
  {R : ResolutionSignature O}
  (Γ : Context R)
  (K : Hole R)
  (source : Entity O) : Type where

  constructor fine
  field
    target     : Entity O
    resolution : HardResolution R Γ K source target

open Fine public

SameMetonymicClass :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  (C : CompressionSignature O R) →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  Fine {O = O} {R = R} Γ K source →
  Fine {O = O} {R = R} Γ K source →
  Type
SameMetonymicClass C {Γ} {K} {source} left right =
  TargetCompatible
    C Γ K
    (target left)
    (target right)

compatibleRefl :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  (value : Fine {O = O} {R = R} Γ K source) →
  SameMetonymicClass C value value
compatibleRefl {C = C} value =
  targetCompatibleRefl C
    (HardResolution.fits (resolution value))

compatibleSym :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  {left right : Fine {O = O} {R = R} Γ K source} →
  SameMetonymicClass C left right →
  SameMetonymicClass C right left
compatibleSym {C = C} {left = left} {right = right} witness =
  targetCompatibleSym C
    (HardResolution.fits (resolution left))
    (HardResolution.fits (resolution right))
    witness

compatibleTrans :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  {first second third : Fine {O = O} {R = R} Γ K source} →
  SameMetonymicClass C first second →
  SameMetonymicClass C second third →
  SameMetonymicClass C first third
compatibleTrans {C = C}
  {first = first} {second = second} {third = third}
  first≈second second≈third =
  targetCompatibleTrans C
    (HardResolution.fits (resolution first))
    (HardResolution.fits (resolution second))
    (HardResolution.fits (resolution third))
    first≈second
    second≈third

Coarse :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  (C : CompressionSignature O R) →
  (Γ : Context R) →
  (K : Hole R) →
  (source : Entity O) →
  Type
Coarse {O = O} {R = R} C Γ K source =
  Fine {O = O} {R = R} Γ K source
    /ₜ SameMetonymicClass C

contract :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  Fine {O = O} {R = R} Γ K source →
  Coarse C Γ K source
contract {O = O} {R = R} {C = C} value = [ value ]

glue :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  (left right : Fine {O = O} {R = R} Γ K source) →
  SameMetonymicClass C left right →
  contract {C = C} left ≡ contract {C = C} right
glue {C = C} left right compatible =
  eq/ left right compatible

Expansion :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  Coarse C Γ K source →
  Type
Expansion {R = R} {C = C} {Γ = Γ} {K = K} {source = source} coarse =
  Σ[ explicit ∈ Fine {R = R} Γ K source ]
    contract {C = C} explicit ≡ coarse

roundTrip :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Context R} →
  {K : Hole R} →
  {source : Entity O} →
  (explicit : Fine {O = O} {R = R} Γ K source) →
  Expansion {C = C} (contract {C = C} explicit)
roundTrip {C = C} explicit =
  explicit , refl

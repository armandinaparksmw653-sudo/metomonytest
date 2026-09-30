{-# OPTIONS --safe --without-K --cubical-compatible #-}

module Metonymy.Ontology where

record OntologySignature : Set₁ where
  field
    Entity : Set
    Edge   : Entity → Entity → Set

open OntologySignature public

data BridgePath
  (O : OntologySignature) :
  Entity O →
  Entity O →
  Set where

  identity :
    (x : Entity O) →
    BridgePath O x x

  edge :
    {x y : Entity O} →
    Edge O x y →
    BridgePath O x y

  compose :
    {x y z : Entity O} →
    BridgePath O x y →
    BridgePath O y z →
    BridgePath O x z

infixl 7 _then_

_then_ :
  {O : OntologySignature} →
  {x y z : Entity O} →
  BridgePath O x y →
  BridgePath O y z →
  BridgePath O x z
_then_ = compose

record BridgeCoherence
  (O : OntologySignature) : Set₁ where

  field
    Basic₂ :
      {x y : Entity O} →
      BridgePath O x y →
      BridgePath O x y →
      Set

open BridgeCoherence public

data Bridge₂
  {O : OntologySignature}
  (Q : BridgeCoherence O) :
  {x y : Entity O} →
  BridgePath O x y →
  BridgePath O x y →
  Set where

  refl₂ :
    {x y : Entity O} →
    {p : BridgePath O x y} →
    Bridge₂ Q p p

  basic₂ :
    {x y : Entity O} →
    {p q : BridgePath O x y} →
    Basic₂ Q p q →
    Bridge₂ Q p q

  sym₂ :
    {x y : Entity O} →
    {p q : BridgePath O x y} →
    Bridge₂ Q p q →
    Bridge₂ Q q p

  trans₂ :
    {x y : Entity O} →
    {p q r : BridgePath O x y} →
    Bridge₂ Q p q →
    Bridge₂ Q q r →
    Bridge₂ Q p r

  compose₂ :
    {x y z : Entity O} →
    {p p' : BridgePath O x y} →
    {q q' : BridgePath O y z} →
    Bridge₂ Q p p' →
    Bridge₂ Q q q' →
    Bridge₂ Q (p then q) (p' then q')

  leftUnit₂ :
    {x y : Entity O} →
    (p : BridgePath O x y) →
    Bridge₂ Q (identity x then p) p

  rightUnit₂ :
    {x y : Entity O} →
    (p : BridgePath O x y) →
    Bridge₂ Q (p then identity y) p

  associate₂ :
    {w x y z : Entity O} →
    (p : BridgePath O w x) →
    (q : BridgePath O x y) →
    (r : BridgePath O y z) →
    Bridge₂ Q
      ((p then q) then r)
      (p then (q then r))

record ResolutionSignature
  (O : OntologySignature) : Set₁ where
  field
    Context           : Set
    Hole              : Set
    Fits              : Context → Hole → Entity O → Set
    HardLicense       :
      (Γ : Context) →
      (K : Hole) →
      {x y : Entity O} →
      BridgePath O x y →
      Set
    PreferenceLicense :
      (Γ : Context) →
      (K : Hole) →
      {x y : Entity O} →
      BridgePath O x y →
      Set
    PromotionEvidence :
      (Γ : Context) →
      (K : Hole) →
      {x y : Entity O} →
      (p : BridgePath O x y) →
      PreferenceLicense Γ K p →
      Set
    promoteLicense :
      (Γ : Context) →
      (K : Hole) →
      {x y : Entity O} →
      (p : BridgePath O x y) →
      (preferred : PreferenceLicense Γ K p) →
      PromotionEvidence Γ K p preferred →
      HardLicense Γ K p

open ResolutionSignature public

record HardResolution
  {O : OntologySignature}
  (R : ResolutionSignature O)
  (Γ : Context R)
  (K : Hole R)
  (x y : Entity O) : Set where

  constructor hardResolution
  field
    bridge  : BridgePath O x y
    fits    : Fits R Γ K y
    license : HardLicense R Γ K bridge

record PreferredResolution
  {O : OntologySignature}
  (R : ResolutionSignature O)
  (Γ : Context R)
  (K : Hole R)
  (x y : Entity O) : Set where

  constructor preferredResolution
  field
    bridge     : BridgePath O x y
    fits       : Fits R Γ K y
    preference : PreferenceLicense R Γ K bridge

promote :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {Γ : Context R} →
  {K : Hole R} →
  {x y : Entity O} →
  (preferred : PreferredResolution R Γ K x y) →
  PromotionEvidence
    R Γ K
    (PreferredResolution.bridge preferred)
    (PreferredResolution.preference preferred) →
  HardResolution R Γ K x y
promote {R = R} {Γ = Γ} {K = K} preferred evidence =
  hardResolution
    (PreferredResolution.bridge preferred)
    (PreferredResolution.fits preferred)
    ( promoteLicense
        R Γ K
        (PreferredResolution.bridge preferred)
        (PreferredResolution.preference preferred)
        evidence
    )

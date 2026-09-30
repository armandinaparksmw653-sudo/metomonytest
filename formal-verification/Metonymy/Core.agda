{-# OPTIONS --cubical #-}

module Metonymy.Core where

open import Cubical.Foundations.Prelude
open import Cubical.Data.Sigma
open import Cubical.Data.Unit
open import Cubical.HITs.TypeQuotients.Base

record Signature : Type₁ where
  field
    Entity      : Type
    Context     : Type
    Hole        : Type
    Relation    : Entity → Entity → Type
    Requirement : Context → Hole → Entity → Type

open Signature public

module Resolution (S : Signature) where
  private
    E = Entity S

  data BridgePath : E → E → Type where
    identity : (x : E) → BridgePath x x
    edge     : {x y : E} → Relation S x y → BridgePath x y
    compose  : {x y z : E} →
               BridgePath x y →
               BridgePath y z →
               BridgePath x z

  Admissible :
    Context S →
    Hole S →
    E →
    E →
    Type
  Admissible Γ K x y =
    BridgePath x y × Requirement S Γ K y

  Fine :
    Context S →
    Hole S →
    E →
    Type
  Fine Γ K x =
    Σ[ y ∈ E ] Admissible Γ K x y

  SameMetonymicClass :
    {Γ : Context S} →
    {K : Hole S} →
    {x : E} →
    Fine Γ K x →
    Fine Γ K x →
    Type
  SameMetonymicClass _ _ = Unit

  Coarse :
    Context S →
    Hole S →
    E →
    Type
  Coarse Γ K x =
    Fine Γ K x /ₜ SameMetonymicClass

  contract :
    {Γ : Context S} →
    {K : Hole S} →
    {x : E} →
    Fine Γ K x →
    Coarse Γ K x
  contract fine = [ fine ]

  glue :
    {Γ : Context S} →
    {K : Hole S} →
    {x : E} →
    (a b : Fine Γ K x) →
    contract a ≡ contract b
  glue a b = eq/ a b tt

  Expansion :
    {Γ : Context S} →
    {K : Hole S} →
    {x : E} →
    Coarse Γ K x →
    Type
  Expansion {Γ} {K} {x} coarse =
    Σ[ fine ∈ Fine Γ K x ] contract fine ≡ coarse

  roundTrip :
    {Γ : Context S} →
    {K : Hole S} →
    {x : E} →
    (fine : Fine Γ K x) →
    Expansion (contract fine)
  roundTrip fine = fine , refl

  data Derivation
    (Γ : Context S)
    (K : Hole S)
    (x : E) : Type where

    implicit :
      Derivation Γ K x

    explicit :
      (y : E) →
      Admissible Γ K x y →
      Derivation Γ K x

    metonymy :
      (y : E) →
      (certificate : Admissible Γ K x y) →
      implicit ≡ explicit y certificate

{-# OPTIONS --cubical #-}

module Metonymy.Soundness where

open import Cubical.Foundations.Prelude
open import Metonymy.Core

module _ (S : Signature) where
  open Resolution S

  metonymyIsComposable :
    {Γ : Context S} →
    {K : Hole S} →
    {x y : Entity S} →
    (certificate : Admissible Γ K x y) →
    {Target : Type} →
    (grammarContext : Derivation Γ K x → Target) →
    grammarContext implicit
      ≡
    grammarContext (explicit y certificate)
  metonymyIsComposable certificate grammarContext =
    cong grammarContext (metonymy _ certificate)

  contractionKeepsOriginalExpansion :
    {Γ : Context S} →
    {K : Hole S} →
    {x : Entity S} →
    (fine : Fine Γ K x) →
    Expansion (contract fine)
  contractionKeepsOriginalExpansion = roundTrip

  admissibleMeaningsHaveSameCompressedImage :
    {Γ : Context S} →
    {K : Hole S} →
    {x : Entity S} →
    (a b : Fine Γ K x) →
    contract a ≡ contract b
  admissibleMeaningsHaveSameCompressedImage = glue

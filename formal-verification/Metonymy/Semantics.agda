{-# OPTIONS --cubical #-}

module Metonymy.Semantics where

open import Cubical.Foundations.Prelude
open import Metonymy.Grammar
open import Metonymy.Cell
open import Metonymy.Completion

record SemanticModel
  {G : GrammarSignature}
  (M : MetonymicSystem G)
  (A B : Interface G) : Type₁ where

  field
    Meaning :
      Type

    interpretRaw :
      RawDerivation G A B →
      Meaning

    respectCell :
      {f g : RawDerivation G A B} →
      (cell : HardCell M f g) →
      interpretRaw f ≡ interpretRaw g

    respectCoherence :
      {f g : RawDerivation G A B} →
      {left right : HardCell M f g} →
      (square : Cell₂ M left right) →
      respectCell left ≡ respectCell right

open SemanticModel public

interpret :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  {A B : Interface G} →
  (S : SemanticModel M A B) →
  Completion M A B →
  Meaning S
interpret S (raw derivation) =
  interpretRaw S derivation
interpret S (metonymic cell i) =
  respectCell S cell i
interpret S (coherent square i j) =
  respectCoherence S square i j

factorization :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  {A B : Interface G} →
  (S : SemanticModel M A B) →
  (derivation : RawDerivation G A B) →
  interpret S (raw derivation)
    ≡
  interpretRaw S derivation
factorization S derivation =
  refl

semanticCell :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  {A B : Interface G} →
  (S : SemanticModel M A B) →
  {f g : RawDerivation G A B} →
  (cell : HardCell M f g) →
  Path
    (Meaning S)
    (interpret S (raw f))
    (interpret S (raw g))
semanticCell S cell =
  respectCell S cell

{-# OPTIONS --cubical #-}

module Metonymy.Completion where

open import Cubical.Foundations.Prelude
open import Metonymy.Grammar
open import Metonymy.Cell

data Completion
  {G : GrammarSignature}
  (M : MetonymicSystem G)
  (A B : Interface G) : Type where

  raw :
    RawDerivation G A B →
    Completion M A B

  metonymic :
    {f g : RawDerivation G A B} →
    (cell : HardCell M f g) →
    raw f ≡ raw g

  coherent :
    {f g : RawDerivation G A B} →
    {left right : HardCell M f g} →
    (square : Cell₂ M left right) →
    metonymic left ≡ metonymic right

preferredDoesNotGeneratePath :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  PreferredCell M f g →
  Type
preferredDoesNotGeneratePath {M = M} preferred =
  PromotionEvidence M preferred

promotedPath :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  (preferred : PreferredCell M f g) →
  PromotionEvidence M preferred →
  Path
    (Completion M A B)
    (raw f)
    (raw g)
promotedPath {M = M} preferred evidence =
  metonymic (promote M preferred evidence)

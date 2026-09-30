{-# OPTIONS --safe --without-K --cubical-compatible #-}

module Metonymy.Cell where

open import Metonymy.Grammar

record MetonymicSystem
  (G : GrammarSignature) : Set₁ where
  field
    HardCell :
      {A B : Interface G} →
      RawDerivation G A B →
      RawDerivation G A B →
      Set

    PreferredCell :
      {A B : Interface G} →
      RawDerivation G A B →
      RawDerivation G A B →
      Set

    PromotionEvidence :
      {A B : Interface G} →
      {f g : RawDerivation G A B} →
      PreferredCell f g →
      Set

    promote :
      {A B : Interface G} →
      {f g : RawDerivation G A B} →
      (preferred : PreferredCell f g) →
      PromotionEvidence preferred →
      HardCell f g

    Basic₂ :
      {A B : Interface G} →
      {f g : RawDerivation G A B} →
      HardCell f g →
      HardCell f g →
      Set

open MetonymicSystem public

data Cell₂
  {G : GrammarSignature}
  (M : MetonymicSystem G) :
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  HardCell M f g →
  HardCell M f g →
  Set where

  refl₂ :
    {A B : Interface G} →
    {f g : RawDerivation G A B} →
    {cell : HardCell M f g} →
    Cell₂ M cell cell

  basic₂ :
    {A B : Interface G} →
    {f g : RawDerivation G A B} →
    {left right : HardCell M f g} →
    Basic₂ M left right →
    Cell₂ M left right

  sym₂ :
    {A B : Interface G} →
    {f g : RawDerivation G A B} →
    {left right : HardCell M f g} →
    Cell₂ M left right →
    Cell₂ M right left

  trans₂ :
    {A B : Interface G} →
    {f g : RawDerivation G A B} →
    {first second third : HardCell M f g} →
    Cell₂ M first second →
    Cell₂ M second third →
    Cell₂ M first third

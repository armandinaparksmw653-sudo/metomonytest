{-# OPTIONS --cubical #-}

module Metonymy.CompilerSoundness where

open import Cubical.Data.List.Base using (List; []; _∷_; _++_)

open import Metonymy.FilteredContext
open import Metonymy.Checker public
  using
    ( preferenceRequirementDoesNotFilter
    ; preferenceRelationDoesNotFilter
    ; preferenceExistentialDoesNotFilter
    )

-- A compiled positive subtree contributes a finite prefix of constraints.
-- Forgetting that prefix is a refinement map back to the incoming context.
prependRefinement :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (constraints : List (Constraint system)) →
  Refinement system Γ (constraints ++ Γ)
prependRefinement [] =
  identityRefinement
prependRefinement (constraint ∷ constraints) =
  composeRefinement
    (prependRefinement constraints)
    headRefinement

-- Soundness of the supported GF-to-constraint compiler at context level:
-- every emitted subtree formula strengthens, never broadens, its input.
compiledGFRefinementSound :
  {system : PositiveConstraintSystem} →
  {category : GFCategory} →
  {Γ : Context system} →
  (tree : PositiveGFTree (Constraint system) category) →
  Refinement
    system
    Γ
    (collectGFConstraints tree ++ Γ)
compiledGFRefinementSound tree =
  prependRefinement (collectGFConstraints tree)

-- Fiber-level corollary: every survivor of all compiled subtree constraints
-- was already a candidate in the incoming fiber.
compiledGFFiberSound :
  {system : PositiveConstraintSystem} →
  {category : GFCategory} →
  {Γ : Context system} →
  (tree : PositiveGFTree (Constraint system) category) →
  Fiber system (collectGFConstraints tree ++ Γ) →
  Fiber system Γ
compiledGFFiberSound {system} {category} {Γ} tree =
  restrict
    {system = system}
    {weaker = Γ}
    {stronger = collectGFConstraints tree ++ Γ}
    (compiledGFRefinementSound
      {system = system}
      {category = category}
      {Γ = Γ}
      tree)

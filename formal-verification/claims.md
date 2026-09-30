# Publication claims and machine-checked witnesses

The command `make formal` checks every theorem below through
`formal/Metonymy/PublicationTheorems.agda`. Names are module-qualified to
make the paper-to-artifact mapping stable.

| Claim | Agda witness | Assumptions and scope |
|---|---|---|
| The executable certificate checker is sound. | `Metonymy.Checker.checkSound` | Relative to the supplied finite `KnowledgeBase`. |
| Checker acceptance is complete for the proof record. | `Metonymy.Checker.checkComplete` | Completeness is for `Admissible`, not for all linguistically valid readings. |
| Runtime acceptance binds the certificate to direction, GF endpoints, predicate, unchanged argument, and safe contraction. | `Metonymy.Checker.runtimeCheckSound` | GF function/entity bindings and facts are inputs to the checker. |
| Any accepted runtime rewrite produces a concrete grammatical hard cell. | `Metonymy.RuntimeBridge.certificateToRuntimeCell` | Requires `runtimeCheck kb before after certificate ≡ true`. |
| Any accepted runtime rewrite produces a cubical path. | `Metonymy.RuntimeBridge.checkedRuntimePath` | Path lives in the free `Completion` for the runtime grammar. |
| Any accepted runtime rewrite is equal in a quotient semantics defined separately from `Completion`. | `Metonymy.RuntimeBridge.checkedRuntimeSemanticEquality` | `RuntimeRelated kb` is itself defined by accepted certificates; this is an internal consistency result, not preservation of an external denotational semantics. |
| The Rumi runtime fixture inhabits the generic theorem. | `Metonymy.RuntimeModel.runtimeGenericSemanticEquality` | Concrete checked KB, GF clauses, and hard certificate. |
| Fine-reading compatibility is reflexive, symmetric, and transitive. | `Metonymy.Compression.compatibleRefl`, `compatibleSym`, `compatibleTrans` | Relative to the target compatibility laws in `CompressionSignature`. |
| Compatible explicit readings are identified by quotient compression. | `Metonymy.Compression.glue`; concrete witness `Metonymy.ConcreteOntology.workBookPath` | Both readings inhabit the same source/context/hole fiber; no converse or pre-compression inequality is claimed. |
| Semantically separated readings do not collapse. | `Metonymy.CompressionTheory.separatedCompressedMeanings`; concrete witness `Metonymy.ConcreteOntology.workOtherDoNotCollapse` | Requires an independent separating `CompressionModel`. |
| Parallel ontology routes induce a grounded grammatical 2-cell. | `Metonymy.ConcreteOntology.routeCoherence`, `ontologyGroundedCell₂` | Concrete executable path interpretation `pathCode`. |
| A checked preference requires explicit promotion evidence before a path can be constructed. | `Metonymy.EndToEnd.promoteAcceptedPreference`; concrete witness `Metonymy.RuntimeModel.runtimePromotedPath` | The generic theorem assumes a realization into a preferred cell; the concrete runtime witness uses a separately instantiated system. |
| Quantified, restricted, negated, focused, anaphorically live, or temporally restricted targets cannot authorize contraction. | `Metonymy.Checker.forgetContextSafe`; reduction witness `Metonymy.RuntimeModel.quantifiedContractionRejected` | Relative to the structured `ForgetContext` bound identically into the runtime clause and certificate. |
| With no hard cells, completion is fully equivalent to raw derivations. | `Metonymy.MetaTheory.rawCompletionEquiv` | Assumes `NoHardCells M`. |
| Independent semantics prevents accidental equality in completion. | `Metonymy.MetaTheory.separatedBySemantics`; concrete witness `Metonymy.RuntimeModel.runtimeNonCollapse` | Requires distinct interpreted meanings. |
| A contextual checker accepts only an accepted runtime rewrite whose target satisfies every supplied lexical constraint. | `Metonymy.Contextual.contextualCheckSound` | Relative to a finite `KnowledgeBase`, lexicalized constraint list, and supplied GF/runtime clauses. |
| Contextual checker acceptance is complete for its runtime and constraint proof record. | `Metonymy.Contextual.contextualCheckComplete` | Completeness is for `ContextualCertificate`, not linguistic completeness. |
| Each finite-snapshot constraint has a decidable extension-or-obstruction outcome. | `Metonymy.Contextual.extensionOrObstruction` | The outcome is relative to the Boolean checker and does not state impossibility in the world. |
| A recorded obstruction excludes extension through that exact constraint. | `Metonymy.Contextual.obstructionSound` | Applies to one candidate and constraint; other candidates can remain in the fiber. |
| Contextual acceptance yields the existing cubical runtime path. | `Metonymy.Contextual.contextualPath` | The contextual layer extends, rather than weakens, `runtimeCheck`. |
| The compiled contextual runtime checker reflects snapshot binding, non-empty action, lexical origins, and every contextual constraint. | `Metonymy.Checker.contextualRuntimeCheckSound`, `contextualRuntimeCheckComplete` | Acceptance is relative to the exact finite KB and supplied snapshot hash. |
| Every intermediate candidate layer is independently decidable by the compiled checker. | `Metonymy.Checker.contextLayerCheckSound`, `contextLayerCheckComplete` | Runtime checks every cumulative constraint prefix; an accepted final layer does not substitute for intermediate checks. |
| A stronger accepted layer restricts to a weaker layer when supplied with an explicit refinement witness. | `Metonymy.ContextualTower.fiberRestriction` | The theorem does not assume arbitrary discourse extensions are monotone. |
| Every accepted layer certificate induces a cubical path. | `Metonymy.ContextualTower.stagePath`; compiled-checker bridge `Metonymy.RuntimeBridge.checkedContextualRuntimePath` | Requires the unchanged hard `runtimeCheck` boundary. |
| Paths for two layers are stable when their contextual certificates explicitly identify the underlying runtime cell. | `Metonymy.ContextualTower.towerPathStability` | Stability is a 2-path induced by an explicit cell-coherence witness; it is not inferred from lexical similarity. |
| The Waterloo fixture has checked paths at graph, action-role, and physics-constrained layers, with explicit path stability between adjacent layers. | `Metonymy.ContextualModel.waterlooStage₀Path`, `waterlooStage₁Path`, `waterlooStage₂Path`, `waterlooStagePathStability₀₁`, `waterlooStagePathStability₁₂` | Concrete finite KB fixture; not evidence of Wikidata completeness. |
| Waterloo City Council is obstructed by the physics relation at the final layer. | `Metonymy.ContextualModel.councilPhysicsObstruction` | Closed-world statement relative to the concrete fixture only. |
| A finite-snapshot obstruction prevents that candidate from extending through the stated constraint. | `Metonymy.ContextualTower.obstructionTerminatesPath` | Candidate- and snapshot-relative only. |
| Contextual candidates are glued only by an explicit compatibility witness, and an empty layer has no rewrite inhabitant. | `Metonymy.ContextualTower.compatibleCandidatesGlue`, `emptyFiberNoRewrite` | Fiber membership alone does not identify different QIDs. |
| Positive lexical contexts induce a contravariant filtered family of proof-relevant bridged cubical types. | `Metonymy.FilteredContext.fiberFunctor`, with laws `restrictIdentity`, `restrictComposition` | Each inhabitant carries `Bridge entity × All Holds`; `Refinement` preserves bridge evidence and maps stronger constraint evidence to weaker evidence. |
| Adding one positive constraint is a lifting problem over the restriction map. | `Metonymy.FilteredContext.extensionIsLiftingProblem`; genuine equivalence `extensionLiftingEquiv` | The untruncated `≃` requires explicit `isProp` assumptions for extension and restriction-fiber witnesses; without them only the two logical directions are claimed. |
| Every finite constraint extension either has a witness or a disjoint obstruction. | `Metonymy.FilteredContext.extensionOrObstruction`, `extensionObstructionDisjoint` | Requires the `Decision` field of `PositiveConstraintSystem`; runtime supplies it through the finite Boolean checker. |
| Proof-carrying paths form a natural section over contextual restriction, including identity and composition coherence. | `Metonymy.FilteredContext.naturalStageSection`, `stagePathNaturality`, `stabilityIdentity`, `stabilityComposition` | The path system fixes one implicit runtime clause per tower; refinement preserves the candidate endpoint. |
| A unique surviving entity licenses the reverse stage path as a safe contraction. | `Metonymy.FilteredContext.UniqueEntity`, `safeContraction`, `uniqueEntityStrengthens`, `contractionPathNaturality` | Runtime uniqueness is uniqueness of entity identifiers, not of `Holds` proofs. This is not inverse expansion and does not infer uniqueness from a stronger layer back to a weaker one. |
| Set-level compatibility compression is functorial and commutes with contextual restriction. | `Metonymy.FilteredContext.restrictCoarse`, `coarseRestrictionIdentity`, `coarseRestrictionComposition`, `compressionNaturality` | Compatibility is an explicit relation on endpoints. This theorem uses a set quotient; richer non-truncated coherence remains in the existing `Completion`. |
| The supported typed GF fragment elaborates exactly and every emitted constraint carries a rule-membership witness. | `Metonymy.FilteredContext.gfElaborationExact`, `gfElaborationCertified` | This is the internal typed GF AST. Correctness of the external GF implementation and text parser remains outside Agda. |
| Equal canonical decoded system/context pairs have equivalent fibers. | `Metonymy.FilteredContext.snapshotSystemTransport` | The premise is equality of decoded structures, not equality of cryptographic hash strings. |
| The executable checker instantiates the abstract filtered family and its proof-carrying path section. | `Metonymy.FilteredRuntime.runtimePositiveSystem`, `runtimeFiberCheckerEquivalence`, `runtimeCandidatePaths`, `runtimeContextualHomotopyTower` | Runtime bridge evidence is the `RuntimeAdmissible` component of each fiber inhabitant; rule provenance must be a member of the supplied rule list. |
| Proof-relevant compatibility compression admits a canonical 2-truncated realization. | `Metonymy.TwoTruncatedContext.RawCoarse₂`, `Coarse₂`, `is2GroupoidCoarse₂` | `Coarse₂ Γ = ∥ Fiber Γ /ₜ Compatible Γ ∥₄`; compatibility paths are retained before truncating above dimension two. |
| Context refinement acts on the 2-truncated compression and compression is natural. | `Metonymy.TwoTruncatedContext.restrictRawCoarse₂`, `restrictCoarse₂`, `compression₂Naturality` | Identity and composition are proved on compression generators by `coarse₂IdentityOnGenerator` and `coarse₂CompositionOnGenerator`. |
| Explicit compatibility 2-cells can be realized as equalities between generated quotient paths. | `Metonymy.TwoTruncatedContext.Compatibility₂System`, `CoherentCompatibility₂` | A binary compatibility relation alone does not manufacture these 2-cells. |
| All coherence strictly above dimension two is proposition-valued. | `Metonymy.TwoTruncatedContext.coherenceAboveDimension₂` | Direct consequence of Cubical `2GroupoidTruncation.squash₄`. |
| The executable runtime has a concrete 2-truncated tower with identity compatibility coherence. | `Metonymy.TwoTruncatedRuntime.runtimeIdentityCompatibility`, `runtimeIdentityCoherence₂`, `runtimeContextual₂Tower` | Richer compatibility than candidate identity requires additional domain-specific 2-cell witnesses. |

## Empirical claims

Empirical results are not Agda theorems. The text-free aggregate in
`evaluation/semeval-location-test-summary.json` records the verified
SemEval-2007 location test run:

- 908 instances;
- all five ablation conditions;
- zero submitted predictions and zero coverage;
- precision/F1 undefined and recall zero.

This is evidence that the present controlled GF grammar is not an
open-domain SemEval system. It is not evidence of competitive NLP accuracy.

The subsequent open-GF elaborator uses only constructors declared by
`grammar/Metonymy.gf`. For each emitted corpus rewrite, Haskell calls the
same compiled `runtimeCheck`; therefore the applicable formal witness
remains `Metonymy.RuntimeBridge.checkedRuntimeSemanticEquality`.
Detection heuristics are not machine-checked claims.

Text-free aggregate baselines are recorded for WiMCor, ConMeC, and
SafeCon-Mini under `evaluation/`. They establish empirical coverage and
error rates, not semantic soundness beyond the checker-relative theorem.

The contextual multi-domain artifact adds 69 deterministic silver instances
(49 expansions and 20 contractions) and nine manually reviewed regression
instances. The silver target sets are
derived from the same frozen graph used by inference and therefore measure
reproducibility, obstruction accounting, checker agreement, and unique-fiber
contraction safety—not independent NLP accuracy. The reviewed set records
9/9 exact fibers, including 4/4 bidirectional contraction cases, but is too
small to support a general accuracy claim.

## Explicit non-claims

The artifact does not prove:

- factual completeness or correctness of Wikidata or VerbNet;
- uniqueness of pragmatic interpretation without a supplied uniqueness
  witness;
- that unique-fiber contraction is inverse expansion;
- open-domain parsing coverage;
- correctness of an unavailable organisation-subtask evaluation;
- contraction accuracy on SemEval, which has no safe-forgetting labels.
- that the included QID fixture is complete or that a lexicalized context
  uniquely identifies an intended referent;
- tower-level path coherence without an explicit refinement and runtime-cell
  coherence witness.
- that every natural-language context update is positive or monotone;
- that the supplied endpoint compatibility relation is linguistically
  complete;
- a functorial law for arbitrary non-truncated quotients without the required
  higher compatibility coherences.
- a globally inhabited `Coarse₂Pseudofunctor` for arbitrary compatibility;
  the module exposes this interface, while the canonical construction proves
  refinement maps, naturality, and laws on quotient generators.

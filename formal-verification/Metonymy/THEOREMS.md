# Machine-checked theorem index

All witnesses below are imported by `PublicationTheorems.agda` and checked by
`make formal`. “Relative” means relative to explicitly supplied finite
snapshots, lexical bindings, rule membership, compatibility, and semantic
models.

## Main theorem

For a positive lexical constraint system:

```text
Fiber Γ = Σ candidate. Bridge candidate × All (Holds candidate) Γ
```

the fibers form a contravariant filtered family in Cubical `Type`.
Proof-carrying paths form a natural section. Adding one constraint is a
decidable lifting problem with a disjoint obstruction. Compatibility
compression is functorial at set level and has a proof-relevant 2-truncated
realization.

Witnesses:

| Statement | Agda witness |
|---|---|
| Filtered family of bridged cubical types | `FilteredContext.fiberFunctor` |
| Identity law | `FilteredContext.restrictIdentity` |
| Composition law | `FilteredContext.restrictComposition` |
| Bundled theorem | `FilteredContext.contextualHomotopyTower` |
| Executable instantiation | `FilteredRuntime.runtimeContextualHomotopyTower` |

## Lexicalized GF elaboration

The internal supported GF AST is indexed by grammatical category and covers
predication, complementation, PP modification, adjective modification, and
determiners.

| Statement | Agda witness |
|---|---|
| Structural elaboration is exact | `FilteredContext.gfElaborationExact` |
| Every emitted constraint has rule-membership evidence | `FilteredContext.gfElaborationCertified` |
| Generic lexical collection is exact | `FilteredContext.elaborationExact` |
| Runtime origins occur in the supplied tree | `ContextualTower.elaborationBindsLexemes` |

The external GF parser is an untrusted producer. The checked claim begins at
the decoded internal AST.

## Restriction and lifting obstruction

For extension by constraint `c`, `ExtensionSpace c x` is the evidence needed
to lift `x` through the restriction map.

| Statement | Agda witness |
|---|---|
| Extension maps to the restriction fiber | `FilteredContext.extensionToRestrictionFiber` |
| Restriction-fiber inhabitant maps back to extension | `FilteredContext.restrictionFiberToExtension` |
| Logical equivalence | `FilteredContext.extensionIsLiftingProblem` |
| Genuine equivalence under explicit `isProp` assumptions | `FilteredContext.extensionLiftingEquiv` |
| Extension or obstruction | `FilteredContext.extensionOrObstruction` |
| Outcomes are disjoint | `FilteredContext.extensionObstructionDisjoint` |
| Executable obstruction soundness | `Contextual.obstructionSound` |
| Obstruction terminates that candidate path | `ContextualTower.obstructionTerminatesPath` |

An obstruction states failure relative to the supplied finite snapshot. It is
not impossibility in natural language or the world.

## Natural proof-carrying paths

| Statement | Agda witness |
|---|---|
| Path for every fiber inhabitant | `FilteredContext.stagePath` |
| Naturality under refinement | `FilteredContext.stagePathNaturality` |
| Identity coherence | `FilteredContext.stabilityIdentity` |
| Composition coherence | `FilteredContext.stabilityComposition` |
| Bundled natural section | `FilteredContext.naturalStageSection` |
| Runtime paths use hard bridge evidence | `FilteredRuntime.runtimeCandidatePaths` |
| Accepted contextual certificate gives a completion path | `RuntimeBridge.checkedContextualRuntimePath` |

Naturality fixes one implicit runtime clause per tower. Arbitrary non-monotone
discourse updates are outside this theorem.

## Positive GF compiler soundness

| Statement | Agda witness |
|---|---|
| Every supported GF constructor elaborates to its collected constraints | `FilteredContext.gfElaborationExact` |
| Every elaborated constraint belongs to the versioned rule snapshot | `FilteredContext.gfElaborationCertified` |
| A finite compiled prefix induces a refinement | `CompilerSoundness.prependRefinement` |
| Compiled subtree constraints refine the incoming context | `CompilerSoundness.compiledGFRefinementSound` |
| Every inhabitant of the compiled fiber restricts to the incoming fiber | `CompilerSoundness.compiledGFFiberSound` |
| Preference requirements do not filter the hard fiber | `CompilerSoundness.preferenceRequirementDoesNotFilter` |
| Preference relations do not filter the hard fiber | `CompilerSoundness.preferenceRelationDoesNotFilter` |
| Existential preferences do not filter the hard fiber | `CompilerSoundness.preferenceExistentialDoesNotFilter` |

The supported positive grammar includes direct objects, adjective–noun
composition, `in/about/with/for` PP modifiers, and relative-clause
composition. The theorem is parametric in the constraint interpretation; it
does not claim that an external FrameNet projection is linguistically
correct. That claim remains tied to the versioned projection provenance.
The compiler-specific statements are isolated in
`CompilerSoundness.agda`; generic filtered-family definitions remain in
`FilteredContext.agda`, while executable Boolean reflection remains in
`Checker.agda`.

## Unique-fiber contraction

The reverse path `sym (stagePath selected)` always exists for a fiber
inhabitant. Using it as a *safe contraction* requires uniqueness of the
selected entity in the final layer:

```text
UniqueEntity selected = ∀ value. candidate selected ≡ candidate value
```

| Statement | Agda witness |
|---|---|
| Unique fiber inhabitant (stronger, proof-relevant) | `FilteredContext.UniqueFiber` |
| Unique entity identifier (runtime-aligned) | `FilteredContext.UniqueEntity` |
| Unique fiber implies unique entity | `FilteredContext.uniqueFiberImpliesUniqueEntity` |
| Uniqueness at a weaker layer implies uniqueness after strengthening | `FilteredContext.uniqueEntityStrengthens` |
| Safe contraction is the reverse stage path under uniqueness | `FilteredContext.safeContraction` |
| Reverse paths remain natural under refinement | `FilteredContext.contractionPathNaturality` |

Uniqueness of entity identifiers is what the executable
`contextualContractionChecked` gate checks. Unique proofs of `Holds` or
unique bridges are a stronger `UniqueFiber` hypothesis and are not required
for the runtime gate. Adding constraints can only preserve uniqueness
(`uniqueEntityStrengthens`); uniqueness at a stronger layer does not imply
uniqueness at a weaker layer. Safe contraction is not the inverse of
expansion: an expansion fiber with two survivors has no unique contraction.

Generic-reading contraction remains the older `HasSort GenericReading` gate
and is independent of `UniqueEntity`.

## Set-level compatibility compression

| Statement | Agda witness |
|---|---|
| Compatibility survives refinement | `FilteredContext.restrictPreservesCompatibility` |
| Restriction on compressed fibers | `FilteredContext.restrictCoarse` |
| Identity | `FilteredContext.coarseRestrictionIdentity` |
| Composition | `FilteredContext.coarseRestrictionComposition` |
| Compression naturality | `FilteredContext.compressionNaturality` |
| Glue requires explicit compatibility | `ContextualTower.compatibleCandidatesGlue` |
| Empty fiber cannot contain a rewrite | `ContextualTower.emptyFiberNoRewrite` |

## Proof-relevant 2-truncated compression

```text
RawCoarse₂ Γ = Fiber Γ /ₜ Compatible Γ
Coarse₂ Γ    = ∥ RawCoarse₂ Γ ∥₄
```

The first quotient retains generated compatibility paths. Cubical
2-groupoid truncation removes structure strictly above dimension two.

| Statement | Agda witness |
|---|---|
| `Coarse₂` is a 2-groupoid | `TwoTruncatedContext.is2GroupoidCoarse₂` |
| Raw quotient refinement | `TwoTruncatedContext.restrictRawCoarse₂` |
| 2-truncated refinement | `TwoTruncatedContext.restrictCoarse₂` |
| Compression naturality | `TwoTruncatedContext.compression₂Naturality` |
| Identity on generators | `TwoTruncatedContext.coarse₂IdentityOnGenerator` |
| Composition on generators | `TwoTruncatedContext.coarse₂CompositionOnGenerator` |
| Explicit parallel compatibility 2-cells | `TwoTruncatedContext.Compatibility₂System` |
| Realization as equality of quotient paths | `TwoTruncatedContext.CoherentCompatibility₂` |
| Coherence above dimension two is unique | `TwoTruncatedContext.coherenceAboveDimension₂` |
| Bundled fine/2-truncated tower | `TwoTruncatedContext.contextual₂Tower` |
| Runtime identity compatibility | `TwoTruncatedRuntime.runtimeIdentityCompatibility` |
| Runtime compatibility 2-cell realization | `TwoTruncatedRuntime.runtimeIdentityCoherence₂` |
| Runtime 2-truncated tower | `TwoTruncatedRuntime.runtimeContextual₂Tower` |
| Non-trivial real-data compatibility (Novalis's two works) | `NovalisCoarseModel.novalisCompatibility` |
| Non-trivial 2-cell coherence, realized | `NovalisCoarseModel.novalisCoherence₂` |
| Two distinct real entities identified at the coarse level | `NovalisCoarseModel.hymnsHeinrichIdentified` |
| Non-trivial real-data compatibility (Eswatini's two cabinets) | `EswatiniCoarseModel.eswatiniCompatibility` |
| Non-trivial 2-cell coherence, realized | `EswatiniCoarseModel.eswatiniCoherence₂` |
| Two distinct real entities identified at the coarse level | `EswatiniCoarseModel.ambroseRussellIdentified` |
| Non-trivial real-data compatibility (Rijeka's two football clubs) | `RijekaCoarseModel.rijekaCompatibility` |
| Non-trivial 2-cell coherence, realized | `RijekaCoarseModel.rijekaCoherence₂` |
| Two distinct real entities identified at the coarse level, at a non-empty context | `RijekaCoarseModel.hnkOrijentIdentified` |

`TwoTruncatedRuntime`'s own runtime compatibility is bare equality, which
identifies nothing beyond what was already equal. Three modules
instantiate the same 2-truncated tower against real Wikidata data with a
genuinely non-trivial relation -- "reached from the same source by the
same bridge relation" -- for every currently-known genuinely non-unique
example in the curated database:
`NovalisCoarseModel` (Novalis, Q60684, and his two attested literary
works, Q128670 and Q58178849; the certificate's own requirement, at the
empty context); `EswatiniCoarseModel` (Eswatini, Q1050, and its two
attested cabinet formations, Q114513825 and Q123554307; same shape);
`RijekaCoarseModel` (Rijeka, Q1647, and its two attested football clubs,
Q318969 and Q1447572; at a *non-empty* context, since the sentence's own
"season" constraint is a second, separate layer on top of the
certificate's requirement -- compression is shown here to apply only once
narrowing from the sentence itself is already exhausted, not to compete
with it). Each proves the two distinct real entities are identified at
the coarse level, with 2-cell coherence realized for that relation. These
are the same fixtures the Haskell engine's test suite already treats as
real, non-unique two-candidate results (`Metonymy.AuthorWork`,
`Metonymy.Eswatini`, `Metonymy.Rijeka`); these three modules supply their
coarse-reading counterpart. (Waterloo's own three-way non-uniqueness is
narrowed to a unique candidate by a second real lexical signal --
"in physics" -- within the same sentence, so it never reaches this
situation; these three are the ones for which the sentence itself
supplies no such further signal.)

A fourth, three-way case -- `Metonymy.FleetStreet` (Fleet Street,
Q846686, and the three national newspapers historically headquartered
there, Q610190/Q210534/Q192621, all sharing the "daily newspaper" sort)
-- is checked not through a standalone per-entity Agda model but through
the general, already-proven `GeneralCoarseCompatibility.compatibilityCheck`
running live inside the Haskell engine's own pipeline
(`Metonymy.ContextualChecked.contextualCoarseReading`, itself verified
per-pairing via `Metonymy.Verified.verifyCompatibilityWithAgda`) -- the
same generic checker the negative Waterloo proof
(`universityCouncilNotCompatible`) already certifies safe. Unlike the
three examples above, this one is not grounded in a single attested
WiMCor/ConMeC corpus sentence: `Metonymy.FleetStreet`'s own docstring
documents its different evidentiary basis (a cited, documented pattern
of deliberate collective reference, not a transcribed sentence) and
should be read alongside that disclosure.

`Coarse₂Pseudofunctor` states global identity/composition obligations for an
arbitrary compatibility system. The canonical construction proves maps,
naturality, and laws on quotient generators. A global inhabitant for richer
compatibility requires domain-specific compatibility 2-cells and is not
claimed automatically.

## Executable checker reflection

| Statement | Agda witness |
|---|---|
| Base certificate checker soundness | `Checker.checkSound` |
| Base checker completeness | `Checker.checkComplete` |
| Runtime checker soundness | `Checker.runtimeCheckSound` |
| Layer checker soundness/completeness | `Checker.contextLayerCheckSound`, `contextLayerCheckComplete` |
| Contextual runtime soundness/completeness | `Checker.contextualRuntimeCheckSound`, `contextualRuntimeCheckComplete` |
| Dependent evidence agrees with finite checker | `FilteredRuntime.runtimeFiberCheckerEquivalence` |
| Unknown rule provenance is rejected | `Checker.allProvenanceKnown` through `contextLayerCheck` |

## Concrete Waterloo model

| Statement | Agda witness |
|---|---|
| Paths at graph/action/physics layers | `ContextualModel.waterlooStage₀Path`, `waterlooStage₁Path`, `waterlooStage₂Path` |
| Adjacent path stability | `ContextualModel.waterlooStagePathStability₀₁`, `waterlooStagePathStability₁₂` |
| Council physics obstruction | `ContextualModel.councilPhysicsObstruction` |

## Existing completion and semantics

| Statement | Agda witness |
|---|---|
| Hard cell generates a path | `EndToEnd.hardCellPath` |
| Preference requires promotion | `EndToEnd.promoteAcceptedPreference` |
| Runtime certificate generates a hard cell | `RuntimeBridge.certificateToRuntimeCell` |
| Runtime path | `RuntimeBridge.checkedRuntimePath` |
| Runtime semantic equality | `RuntimeBridge.checkedRuntimeSemanticEquality` |
| Compatibility quotient glue | `Compression.glue` |
| Unique round trip under uniqueness hypothesis | `CompressionTheory.uniqueRoundTrip` |
| Separation prevents collapse | `CompressionTheory.separatedCompressedMeanings` |
| Conservativity without hard cells | `MetaTheory.rawCompletionEquiv`, `conservativity` |
| Independent semantics separates completion points | `MetaTheory.separatedBySemantics` |
| Concrete ontology route coherence | `ConcreteOntology.routeCoherence`, `ontologyGroundedCell₂` |

## Snapshot invariance

| Statement | Agda witness |
|---|---|
| Equal decoded system/context pairs have equivalent fibers | `FilteredContext.snapshotSystemTransport` |

Cryptographic hash equality alone is not treated as mathematical equality.
Hashes are runtime guards; the theorem assumes equality of canonical decoded
structures.

## Explicit non-claims

The artifact does not prove:

- correctness or completeness of GF parsing arbitrary text;
- factual correctness or completeness of Wikidata, WordNet, VerbNet, or
  OpenAlex;
- uniqueness of intended pragmatic interpretation;
- that safe contraction is the inverse of expansion, or that uniqueness at a
  stronger layer implies uniqueness at a weaker layer;
- monotonicity of arbitrary negation, quantification, anaphora, or discourse
  update;
- a global `Coarse₂Pseudofunctor` for arbitrary compatibility without supplied
  higher coherence;
- external denotational equivalence beyond the stated semantic model;
- competitive NLP accuracy from the formal theorems alone.

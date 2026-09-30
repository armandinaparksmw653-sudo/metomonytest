# Main theorem

**Contextual homotopy fiber.**
Let \(S\) be a finite snapshot (entities, bridges, facts), \(R\) a versioned
rule set, and \(\Gamma\) a finite list of positive lexicalized constraints,
each bound to a node of a supported GF tree and to a rule in \(R\).

Define

```text
Fiber(Γ) = Σ x. Bridge(x) × All(Holds(x), Γ)
```

Then the following hold.

## 1. Filtered family

If \(\Gamma'\) refines \(\Gamma\) by adding constraints, there is a
restriction map

```text
restrict : Fiber(Γ') → Fiber(Γ)
```

that is the identity on empty extension and functorial under composition of
refinements.

## 2. Natural proof-carrying paths

Every inhabitant of a fiber has a proof-carrying path (a certificate). The
section is natural: restricting the context does not change an already
accepted path.

## 3. Decidable lifting step

For a single new constraint \(c\), either there is lifting evidence along
`restrict`, or there is a disjoint obstruction. There is no third outcome.
An empty fiber contains no rewrite.

## 4. Compilation

Constraints collected from a supported GF subtree (SVO, Adj+N,
`in`/`about`/`with`/`for`, relative clause) form a refinement. A
selectional preference does not filter the hard fiber.

## 5. Safe contraction

The reverse path is a safe contraction only if the final layer contains a
unique entity (`UniqueEntity`). Two survivors yield no contraction.

## Scope

All statements are relative to \(S\), \(R\), and the decoded tree. The
theorem does not claim completeness of English, factual correctness of
Wikidata, or uniqueness of an intended pragmatic reading.

## Witnesses

| Claim | Agda |
|---|---|
| Filtered family and natural section | `FilteredContext.contextualHomotopyTower` |
| Compiled GF subtree is a refinement | `CompilerSoundness.compiledGFRefinementSound` |
| Unique-entity contraction | `FilteredContext.safeContraction` |

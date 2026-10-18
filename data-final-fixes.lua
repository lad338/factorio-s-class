-- Unlocks this mod's recipe the moment automobilism is researched,
-- rather than adding a separate technology.
table.insert(data.raw["technology"]["automobilism"].effects, {
  type = "unlock-recipe",
  recipe = "s-class",
})

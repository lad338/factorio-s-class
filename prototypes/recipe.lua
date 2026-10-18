-- The "s-class" item prototype lives in prototypes/entity/s-class.lua,
-- not here -- the entity's `minable.result` needs it to already exist.
-- Ingredients are double vanilla car's own recipe amounts.
data:extend({
  {
    type = "recipe",
    name = "s-class",
    enabled = false,
    energy_required = 2,
    ingredients = {
      {type = "item", name = "engine-unit", amount = 16},
      {type = "item", name = "iron-plate", amount = 40},
      {type = "item", name = "steel-plate", amount = 10},
    },
    results = {{type = "item", name = "s-class", amount = 1}},
  },
})

local ICONPATH = "__s-class__/graphics/icons/"
local ENTITYPATH = "__s-class__/graphics/entity/s-class/"
local FRAME_SIZE = 512  -- must match the rendered frame size in graphics/entity/s-class/

data:extend({
  {
    type = "car",
    name = "s-class",
    icon = ICONPATH .. "s-class-icon.png",
    icon_size = 64,
    flags = {"placeable-neutral", "player-creation", "placeable-off-grid", "not-flammable"},
    minable = {mining_time = 0.5, result = "s-class"},
    -- Width copied from vanilla tank; length increased from tank's 2.6
    -- tiles to 4.6, matching the model's real length:width ratio
    -- (5.40m:2.13m, ~2.54:1) applied to the 1.8-tile width. Shifted
    -- 0.3 tiles north (-Y) of center so it lines up with the sprite
    -- when facing north/south -- simpler than shifting the sprite
    -- itself, which would also require re-deriving the shadow layer's
    -- own relative shift.
    collision_box = {{-0.9, -2.6}, {0.9, 2.0}},
    selection_box = {{-0.9, -2.6}, {0.9, 2.0}},
    drawing_box_vertical_extension = 0.5,
    animation = {
      layers = {
        {
          filename = ENTITYPATH .. "s-class-spritesheet.png",
          width = FRAME_SIZE,
          height = FRAME_SIZE,
          frame_count = 1,
          direction_count = 36,
          line_length = 6,
          scale = 0.5,
          shift = {0, 0},
        },
        {
          filename = ENTITYPATH .. "s-class-spritesheet-shadow.png",
          width = FRAME_SIZE,
          height = FRAME_SIZE,
          frame_count = 1,
          direction_count = 36,
          line_length = 6,
          scale = 0.5,
          -- Without an offset this sits directly under the opaque main
          -- layer and is invisible.
          shift = util.by_pixel(10, 6),
          draw_as_shadow = true,
        },
      },
    },
    max_health = 2000,
    energy_per_hit_point = 0.5,
    resistances = {
      {type = "fire", decrease = 20, percent = 80},
      {type = "physical", decrease = 20, percent = 80},
      {type = "impact", decrease = 50, percent = 80},
      {type = "explosion", decrease = 20, percent = 80},
      {type = "acid", decrease = 20, percent = 80},
    },
    equipment_grid = "medium-equipment-grid",
    inventory_size = 80,
    trash_inventory_size = 20,
    energy_source = {
      type = "burner",
      fuel_inventory_size = 4,
      effectivity = 1,
    },
    consumption = "1000kW",
    effectivity = 0.9,
    weight = 1000,
    braking_force = 75000,
    friction_force = 0.001,
    rotation_speed = 0.01,
    rotation_snap_angle = 0.01,
    stop_trigger_speed = 0.1,
    terrain_friction_modifier = 0.1,
    impact_category = "metal-large",
    impact_speed_to_volume_ratio = 5,
    deliver_category = "vehicle",
    is_military_target = true,
    immune_to_all_impacts = true,
    immune_to_rock_impacts = true,
    immune_to_tree_impacts = true,
    surface_conditions = {
      {property = "gravity", min = 1},
    },
    -- No guns -- explicitly unarmed.
    -- No tank_driving -- normal car-style steering, not tank-style pivot.
    allow_remote_driving = true,
    -- No minimap_representation -- car-type has a built-in map fallback;
    -- no custom map icon needed.
    -- Corpse/explosion/sounds are vanilla car's own, not tank's -- this
    -- mod has no tank-specific art/sound assets; only the gameplay
    -- stats above were meant to match tank.
    corpse = "car-remnants",
    dying_explosion = "car-explosion",
    open_sound = {filename = "__base__/sound/car-door-open.ogg", volume = 0.5},
    close_sound = {filename = "__base__/sound/car-door-close.ogg", volume = 0.4},
    sound_no_fuel = {filename = "__base__/sound/fight/car-no-fuel-1.ogg", volume = 0.6},
    stop_trigger = {{type = "play-sound", sound = {filename = "__base__/sound/car-breaks.ogg", volume = 0.2}}},
  },
  {
    -- Co-located with the entity, not in recipe.lua, because
    -- `minable.result` above forward-references this item by name and
    -- Factorio validates that at the end of the full data stage.
    type = "item-with-entity-data",
    name = "s-class",
    icon = ICONPATH .. "s-class-icon.png",
    icon_size = 64,
    subgroup = "transport",
    order = "b[personal-transport]-z[s-class]",
    place_result = "s-class",
    stack_size = 1,
  },
})

-- Normal fuel: reuse vanilla car's own fuel categories, deep-copied (not
-- assigned by reference) -- a shared reference would let a later mod's
-- data-final-fixes.lua alter this table too if it appends its own
-- category to vanilla car's list.
data.raw["car"]["s-class"].energy_source.fuel_categories = table.deepcopy(data.raw["car"]["car"].energy_source.fuel_categories)

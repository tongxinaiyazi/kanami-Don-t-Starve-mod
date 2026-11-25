name = "Kanami isolated engine regression"
description = "Development-only fixtures. Never ship with the character."
author = "Kanami development"
version = "1"
api_version = 10
dst_compatible = true
client_only_mod = false
all_clients_require_mod = false
priority = -2000
configuration_options = {{name="mode",label="Test mode",default="base",options={
    {description="Base",data="base"},{description="Inventory guard",data="guard"},{description="Imprint",data="imprint"},{description="Resources",data="resources"},{description="Void probe",data="void_probe"},
    {description="Interactive",data="interactive"},{description="Void test",data="void"},{description="HappyPatch",data="happy"},{description="Weapons",data="weapons"},{description="Joint weapon input",data="weapon_inputs"},{description="Backpack craft",data="bag"},{description="Review audit",data="audit"},{description="Cave movement and lock-on",data="cave_rifle"}}}}

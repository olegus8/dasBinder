// generated by dasBinder

#include "daScript/daScript.h"

#include "header_to_bind.h"

using namespace das;

//
// enums
//

DAS_BIND_ENUM_CAST(FirstEnum);
DAS_BASE_BIND_ENUM(FirstEnum, FirstEnum
,   FirstEnum_zero
,   FirstEnum_one
,   FirstEnum_two
)
DAS_BIND_ENUM_CAST(SecondEnum);
DAS_BASE_BIND_ENUM(SecondEnum, SecondEnum
,   SecondEnum_zero
,   SecondEnum_one
,   SecondEnum_two
)

//
// structs
//

MAKE_TYPE_FACTORY(FirstStruct, FirstStruct);
struct FirstStructAnnotation
: public ManagedStructureAnnotation<FirstStruct,true,true> {
    FirstStructAnnotation(ModuleLibrary & ml)
    : ManagedStructureAnnotation ("FirstStruct", ml) {
        addField<DAS_BIND_MANAGED_FIELD(bool_field)>("bool_field");
        addField<DAS_BIND_MANAGED_FIELD(int_field)>("int_field");
        addField<DAS_BIND_MANAGED_FIELD(float_field)>("float_field");
    }
    virtual bool isLocal() const override { return true; }
    virtual bool canCopy() const override { return true; }
    virtual bool canMove() const override { return true; }
};
MAKE_TYPE_FACTORY(SecondStruct, SecondStruct);
struct SecondStructAnnotation
: public ManagedStructureAnnotation<SecondStruct,true,true> {
    SecondStructAnnotation(ModuleLibrary & ml)
    : ManagedStructureAnnotation ("SecondStruct", ml) {
        addField<DAS_BIND_MANAGED_FIELD(bool_field)>("bool_field");
        addField<DAS_BIND_MANAGED_FIELD(int_field)>("int_field");
        addField<DAS_BIND_MANAGED_FIELD(float_field)>("float_field");
    }
    virtual bool isLocal() const override { return true; }
    virtual bool canCopy() const override { return true; }
    virtual bool canMove() const override { return true; }
};

class Module_generatedBindings : public Module {
public:
    Module_generatedBindings() : Module("generatedBindings") {
        ModuleLibrary lib;
        lib.addModule(this);
        lib.addBuiltInModule();

        //
        // enums
        //

        addEnumeration(make_smart<EnumerationFirstEnum>());
        addEnumeration(make_smart<EnumerationSecondEnum>());

        //
        // structs
        //

        addAnnotation(make_smart<FirstStructAnnotation>(lib));
        addAnnotation(make_smart<SecondStructAnnotation>(lib));
    }
};

REGISTER_MODULE(Module_generatedBindings);
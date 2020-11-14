// generated by dasBinder

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
// opaque structs
//


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
    void init() {
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
    void init() {
    }
    virtual bool isLocal() const override { return true; }
    virtual bool canCopy() const override { return true; }
    virtual bool canMove() const override { return true; }
};

MAKE_TYPE_FACTORY(StructWithArray, StructWithArray);

struct StructWithArrayAnnotation
: public ManagedStructureAnnotation<StructWithArray,true,true> {
    StructWithArrayAnnotation(ModuleLibrary & ml)
    : ManagedStructureAnnotation ("StructWithArray", ml) {
        addField<DAS_BIND_MANAGED_FIELD(some_ints)>("some_ints");
    }
    void init() {
    }
    virtual bool isLocal() const override { return true; }
    virtual bool canCopy() const override { return true; }
    virtual bool canMove() const override { return true; }
};

MAKE_TYPE_FACTORY(StructWithBitFields, StructWithBitFields);

__forceinline unsigned int StructWithBitFields_get_field24(const StructWithBitFields &s) { return s.field24; }
__forceinline void StructWithBitFields_set_field24(StructWithBitFields &s, unsigned int f) { s.field24 = f; }

__forceinline unsigned int StructWithBitFields_get_field8(const StructWithBitFields &s) { return s.field8; }
__forceinline void StructWithBitFields_set_field8(StructWithBitFields &s, unsigned int f) { s.field8 = f; }

struct StructWithBitFieldsAnnotation
: public ManagedStructureAnnotation<StructWithBitFields,true,true> {
    StructWithBitFieldsAnnotation(ModuleLibrary & ml)
    : ManagedStructureAnnotation ("StructWithBitFields", ml) {
    }
    void init() {
    }
    virtual bool isLocal() const override { return true; }
    virtual bool canCopy() const override { return true; }
    virtual bool canMove() const override { return true; }
};

MAKE_TYPE_FACTORY(StructWithChars, StructWithChars);

struct StructWithCharsAnnotation
: public ManagedStructureAnnotation<StructWithChars,true,true> {
    StructWithCharsAnnotation(ModuleLibrary & ml)
    : ManagedStructureAnnotation ("StructWithChars", ml) {
        addField<DAS_BIND_MANAGED_FIELD(some_chars)>("some_chars");
    }
    void init() {
    }
    virtual bool isLocal() const override { return true; }
    virtual bool canCopy() const override { return true; }
    virtual bool canMove() const override { return true; }
};

MAKE_TYPE_FACTORY(StructWithSizeT, StructWithSizeT);

struct StructWithSizeTAnnotation
: public ManagedStructureAnnotation<StructWithSizeT,true,true> {
    StructWithSizeTAnnotation(ModuleLibrary & ml)
    : ManagedStructureAnnotation ("StructWithSizeT", ml) {
        addField<DAS_BIND_MANAGED_FIELD(my_size)>("my_size");
    }
    void init() {
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
        // opaque structs
        //


        //
        // structs
        //

        addAnnotation(make_smart<FirstStructAnnotation>(lib));
        addAnnotation(make_smart<SecondStructAnnotation>(lib));
        addAnnotation(make_smart<StructWithArrayAnnotation>(lib));
        addAnnotation(make_smart<StructWithBitFieldsAnnotation>(lib));
        
        addExtern<DAS_BIND_FUN(StructWithBitFields_get_field24)>(*this, lib, "StructWithBitFields_get_field24",
            SideEffects::none, "{field.getter_name}");
        addExtern<DAS_BIND_FUN(StructWithBitFields_set_field24)>(*this, lib, "StructWithBitFields_set_field24",
            SideEffects::modifyArgument, "{field.setter_name}");
        
        addExtern<DAS_BIND_FUN(StructWithBitFields_get_field8)>(*this, lib, "StructWithBitFields_get_field8",
            SideEffects::none, "{field.getter_name}");
        addExtern<DAS_BIND_FUN(StructWithBitFields_set_field8)>(*this, lib, "StructWithBitFields_set_field8",
            SideEffects::modifyArgument, "{field.setter_name}");
        addAnnotation(make_smart<StructWithCharsAnnotation>(lib));
        addAnnotation(make_smart<StructWithSizeTAnnotation>(lib));

        //
        // functions
        //

    }
};

REGISTER_MODULE(Module_generatedBindings);
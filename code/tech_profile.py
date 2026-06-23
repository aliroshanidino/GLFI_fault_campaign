# tech_profile.py
class GenericProfile:
    """Knowledge base for Yosys Generic Standard Cells."""
    
    CELL_MAP = {
        "$_dff_p_":   {"domain": "SEQ", "out_pin": "Q"},
        "$_dff_n_":   {"domain": "SEQ", "out_pin": "Q"},
        "$_dff_pp0_": {"domain": "SEQ", "out_pin": "Q"},
        "$_dff_pp1_": {"domain": "SEQ", "out_pin": "Q"},
        
        "$_and_":     {"domain": "COMB", "out_pin": "Y"},
        "$_or_":      {"domain": "COMB", "out_pin": "Y"},
        "$_xor_":     {"domain": "COMB", "out_pin": "Y"},
        "$_nand_":    {"domain": "COMB", "out_pin": "Y"},
        "$_nor_":     {"domain": "COMB", "out_pin": "Y"},
        "$_xnor_":    {"domain": "COMB", "out_pin": "Y"},
        "$_not_":     {"domain": "COMB", "out_pin": "Y"},
        
        "$_mux_":     {"domain": "COMB", "out_pin": "Y"}
    }

    @classmethod
    def get_cell_info(cls, cell_type):
        """Identifies the cell domain and output pin dynamically based on Yosys types."""
        cell_type_lower = cell_type.lower()
        
        for key, val in cls.CELL_MAP.items():
            if cell_type_lower.startswith(key):
                return val
                
        if "dff" in cell_type_lower:
            return {"domain": "SEQ", "out_pin": "Q"}
        
        return {"domain": "COMB", "out_pin": "Y"}
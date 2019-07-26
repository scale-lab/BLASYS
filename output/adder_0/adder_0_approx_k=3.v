module adder_0(pi0, pi1, pi2, pi3, pi4, pi5, pi6, po0, po1, po2, po3);
input pi0, pi1, pi2, pi3, pi4, pi5, pi6;
output po0, po1, po2, po3;
wire k0, k1, k2;
adder_0_w3 DUT1 (pi0, pi1, pi2, pi3, pi4, pi5, pi6, k0, k1, k2);
adder_0_h3 DUT2 (k0, k1, k2, po0, po1, po2, po3);
endmodule

module adder_0_w3(in0, in1, in2, in3, in4, in5, in6, k0, k1, k2);
input in0, in1, in2, in3, in4, in5, in6;
output k0, k1, k2;
assign k0 =   ((~in4 ^ in1) & ((((in6 & (in3 | ~in0)) | (in3 & ~in0)) & (in5 | in2)) | (in5 & in2))) | (((~in3 & in0) | (~in6 & (~in3 | in0))) & (~in5 | ~in2) & (in4 ^ in1)) | (~in5 & ~in2 & (in4 ^ in1));
assign k1 =   ((~in5 ^ in2) & ((in6 & (in3 | ~in0)) | (in3 & ~in0))) | (((~in3 & in0) | (~in6 & (~in3 | in0))) & (in5 ^ in2));
assign k2 =   in6 ? (in3 ^ in0) : (~in3 ^ in0);
endmodule

module adder_0_h3(k0, k1, k2, out0, out1, out2, out3);
input k0, k1, k2;
output out0, out1, out2, out3;
assign out0 = k0;
assign out1 = k0;
assign out2 = k1;
assign out3 = k2;
endmodule
